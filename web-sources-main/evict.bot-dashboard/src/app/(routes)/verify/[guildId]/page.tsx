'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { signIn, useSession } from 'next-auth/react'
import { motion } from 'framer-motion'
import Image from 'next/image'
import HCaptcha from '@hcaptcha/react-hcaptcha'
import { FaLastfm } from 'react-icons/fa'

interface VerificationStatus {
  guild_id: string
  guild_name: string
  guild_icon: string | null
  verification: {
    method: {
      type: 'email' | 'oauth' | 'captcha' | 'questions'
      name: string
      description: string
      provider?: 'lastfm'
    }
    settings: {
      auto_kick: number | null
      rate_limit: number | null
      anti_alt: boolean
      bypass_until: string | null
      block_vpn: boolean
    }
  }
}

interface VerificationSession {
  session: string
  expires_at: string
  requires_review?: boolean
  questions?: {
    id: number
    question: string
    type: 'choice' | 'text'
    options?: string[]
    max_length?: number
  }[]
  verification_data?: {
    email?: { 
      code?: string
      verification_url?: string 
    }
  }
}

const ERROR_MESSAGES = {
  MISSING_AUTHORIZATION: "You need to be logged in to verify.",
  INVALID_TOKEN: "Your session has expired. Please log in again.",
  MISSING_SESSION: "Verification session not found. Please try again.",
  INVALID_SESSION: "Invalid verification session. Please restart verification.",
  SESSION_EXPIRED: "Verification session has expired. Please restart verification.",

  MISSING_FIELDS: "Please provide all required verification information.",
  CODE_NOT_FOUND: "Verification code not found. Please request a new code.",
  INVALID_CODE: "Invalid verification code. Please check and try again.",

  USER_NOT_IN_GUILD: "You are no longer a member of this server.",
  MISSING_PERMISSIONS: "Unable to assign verification role. Please contact server administrators.",

  INTERNAL_ERROR: "An unexpected error occurred. Please try again later.",

  ALREADY_VERIFIED: "You are already verified in this server.",

  VPN_DETECTED: "VPN usage is not allowed for verification. Please disable your VPN and try again.",
} as const

export default function VerifyPage({ params }: { params: { guildId: string } }) {
  const router = useRouter()
  const { data: session, status } = useSession()
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatus | null>(null)
  const [verificationSession, setVerificationSession] = useState<VerificationSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [emailCode, setEmailCode] = useState('')
  const [emailSent, setEmailSent] = useState(false)
  const [isVerified, setIsVerified] = useState(false)
  const [isPendingReview, setIsPendingReview] = useState(false)
  const [sendingEmail, setSendingEmail] = useState(false)
  const [captchaStep, setCaptchaStep] = useState<1 | 2>(1)
  const captchaRef = useRef<HCaptcha>(null)
  const [captchaToken, setCaptchaToken] = useState<string>('')
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [answers, setAnswers] = useState<Record<number, string>>({})

  useEffect(() => {
    if (status === 'unauthenticated') {
      console.log('User not authenticated, redirecting...')
      const returnUrl = `/verify/${params.guildId}`
      router.push(`/login?redirect=${encodeURIComponent(returnUrl)}`)
      return
    }

    if (!params.guildId || !session?.user?.userToken) {
      console.log('Missing required data:', {
        guildId: params.guildId,
        hasToken: !!session?.user?.userToken
      })
      return
    }

    const fetchVerificationStatus = async () => {
      console.log('Starting fetch...')
      try {
        const [ipResponse, verificationResponse] = await Promise.all([
          fetch('https://ipapi.co/json/'),
          fetch(`/api/verification/status/${params.guildId}`, {
            headers: {
              Authorization: `Bearer ${session.user.userToken}`
            }
          })
        ])

        if (!verificationResponse.ok) throw new Error('Failed to fetch verification status')
        if (!ipResponse.ok) throw new Error('Failed to check IP status')
        
        const ipData = await ipResponse.json()
        const verificationData = await verificationResponse.json()
        
        if (verificationData.verified) {
          setError(ERROR_MESSAGES.ALREADY_VERIFIED)
          return
        }

        if (verificationData.verification.settings.block_vpn && 
            (ipData.hosting || ipData.proxy || ipData.tor || ipData.vpn)) {
          setError(ERROR_MESSAGES.VPN_DETECTED)
          return  
        }
        
        setVerificationStatus(verificationData)
      } catch (err) {
        console.error('Error in fetch:', err)
        setError('Failed to load verification status')
      } finally {
        console.log('Setting loading to false')
        setLoading(false)
      }
    }

    console.log('Calling fetchVerificationStatus')
    fetchVerificationStatus()
  }, [params.guildId, status, router, session])

  const startVerification = async () => {
    if (!session?.user?.userToken || !params.guildId || !session?.user?.id) {
      setError(ERROR_MESSAGES.MISSING_AUTHORIZATION)
      return
    }

    setSendingEmail(true)
    try {
      const response = await fetch(`/api/verification/start/${params.guildId}/${session.user.id}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.user.userToken}`
        }
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'INTERNAL_ERROR')
      }
      
      const data = await response.json()
      setVerificationSession(data)
      setEmailSent(true)
    } catch (err) {
      const errorCode = err instanceof Error ? err.message : 'INTERNAL_ERROR'
      setError(ERROR_MESSAGES[errorCode as keyof typeof ERROR_MESSAGES] || ERROR_MESSAGES.INTERNAL_ERROR)
    } finally {
      setSendingEmail(false)
    }
  }

  const submitVerification = async () => {
    if (!session?.user?.userToken || !params.guildId || !verificationSession) {
      setError(ERROR_MESSAGES.MISSING_AUTHORIZATION)
      return
    }

    try {
      const verifyResponse = await fetch(
        `/api/verification/verify/${params.guildId}/${session?.user.id}`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.user.userToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            session: verificationSession.session,
            verification_data: {
              email: {
                code: emailCode
              }
            }
          })
        }
      )

      if (!verifyResponse.ok) {
        const data = await verifyResponse.json()
        throw new Error(data.error || 'INTERNAL_ERROR')
      }

      const data = await verifyResponse.json()
      if (data.status === 'pending_review') {
        setIsPendingReview(true)
      } else if (data.success) {
        setIsVerified(true)
      } else {
        throw new Error(data.error || 'INTERNAL_ERROR')
      }
    } catch (err) {
      const errorCode = err instanceof Error ? err.message : 'INTERNAL_ERROR'
      setError(ERROR_MESSAGES[errorCode as keyof typeof ERROR_MESSAGES] || ERROR_MESSAGES.INTERNAL_ERROR)
    }
  }

  const handleCaptchaVerify = async (token: string) => {
    setCaptchaToken(token)
    try {
      const verifyResponse = await fetch(
        `/api/verification/verify/${params.guildId}/${session?.user.id}`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session?.user?.userToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            session: verificationSession?.session,
            token: token
          })
        }
      )

      if (!verifyResponse.ok) {
        const data = await verifyResponse.json()
        throw new Error(data.error || 'INTERNAL_ERROR')
      }

      const data = await verifyResponse.json()
      if (data.success) {
        setIsVerified(true)
      }
    } catch (err) {
      const errorCode = err instanceof Error ? err.message : 'INTERNAL_ERROR'
      setError(ERROR_MESSAGES[errorCode as keyof typeof ERROR_MESSAGES] || ERROR_MESSAGES.INTERNAL_ERROR)
      captchaRef.current?.resetCaptcha()
    }
  }

  const startCaptchaVerification = async () => {
    try {
      const response = await fetch(`/api/verification/start/${params.guildId}/${session?.user.id}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session?.user?.userToken}`
        }
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'INTERNAL_ERROR')
      }
      
      const data = await response.json()
      setVerificationSession(data)
      setCaptchaStep(2)
    } catch (err) {
      const errorCode = err instanceof Error ? err.message : 'INTERNAL_ERROR'
      setError(ERROR_MESSAGES[errorCode as keyof typeof ERROR_MESSAGES] || ERROR_MESSAGES.INTERNAL_ERROR)
    }
  }

  const renderVerificationMethod = () => {
    if (verificationStatus?.verification.method.type === 'questions') {
      return (
        <div className="space-y-6">
          <div className="text-center">
            <div className="flex flex-col items-center gap-4 mb-6">
              {verificationStatus?.guild_icon && (
                <div className="relative w-24 h-24">
                  <Image
                    src={verificationStatus.guild_icon}
                    alt={verificationStatus.guild_name}
                    fill
                    unoptimized
                    className="object-cover rounded-full"
                  />
                </div>
              )}
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {verificationStatus.guild_name}
                </h2>
                <h3 className="text-white/60 text-sm mt-1">
                  {verificationStatus.verification.method.name}
                </h3>
              </div>
            </div>

            {!verificationSession ? (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <p className="text-white/60 text-sm">
                  {verificationStatus.verification.method.description}
                </p>
                <button
                  onClick={startVerification}
                  className="w-full bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 
                           hover:border-white/10 text-white font-medium py-3 px-4 rounded-lg 
                           transition-all duration-200 flex items-center justify-center gap-2"
                >
                  Start Verification
                </button>
              </motion.div>
            ) : (
              verificationSession.questions ? (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium text-white">
                    {verificationSession.questions[currentQuestion].question}
                  </h3>

                  {verificationSession.questions[currentQuestion].type === 'choice' ? (
                    <div className="space-y-2">
                      {verificationSession.questions[currentQuestion].options?.map((option) => (
                        <button
                          key={option}
                          onClick={() => {
                            setAnswers(prev => ({
                              ...prev,
                              [verificationSession.questions![currentQuestion].id]: option
                            }))
                            if (currentQuestion < verificationSession.questions!.length - 1) {
                              setCurrentQuestion(prev => prev + 1)
                            }
                          }}
                          className={`w-full text-left px-4 py-3 rounded-lg transition-all ${
                            answers[verificationSession.questions![currentQuestion].id] === option
                              ? 'bg-white/10 text-white'
                              : 'bg-white/[0.02] hover:bg-white/[0.05] text-white/80'
                          }`}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <textarea
                      value={answers[verificationSession.questions[currentQuestion].id] || ''}
                      onChange={(e) => setAnswers(prev => ({
                        ...prev,
                        [verificationSession.questions![currentQuestion].id]: e.target.value
                      }))}
                      maxLength={verificationSession.questions[currentQuestion].max_length}
                      className="w-full bg-white/[0.02] text-white rounded-lg p-4 min-h-[100px]"
                      placeholder="Type your answer here..."
                    />
                  )}

                  <div className="flex justify-between">
                    <button
                      onClick={() => setCurrentQuestion(prev => prev - 1)}
                      disabled={currentQuestion === 0}
                      className="text-white/60 hover:text-white disabled:opacity-50"
                    >
                      Previous
                    </button>
                    {currentQuestion === verificationSession.questions.length - 1 ? (
                      <button
                        onClick={async () => {
                          try {
                            const response = await fetch(
                              `/api/verification/verify/${params.guildId}/${session?.user.id}`,
                              {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                  Authorization: `Bearer ${session?.user?.userToken}`
                                },
                                body: JSON.stringify({
                                  session: verificationSession.session,
                                  answers
                                })
                              }
                            )
                            
                            const data = await response.json()
                            
                            if (data.status === 'pending_review') {
                              setIsPendingReview(true)
                              return
                            }
                            
                            if (data.success) {
                              setIsVerified(true)
                            } else {
                              setError(ERROR_MESSAGES.INTERNAL_ERROR)
                            }
                          } catch (err) {
                            setError(ERROR_MESSAGES.INTERNAL_ERROR)
                          }
                        }}
                        className="bg-white/[0.02] hover:bg-white/[0.05] text-white px-4 py-2 rounded-lg"
                      >
                        Submit
                      </button>
                    ) : (
                      <button
                        onClick={() => setCurrentQuestion(prev => prev + 1)}
                        disabled={!answers[verificationSession.questions[currentQuestion].id]}
                        className="text-white/60 hover:text-white disabled:opacity-50"
                      >
                        Next
                      </button>
                    )}
                  </div>
                </div>
              ) : null
            )}
          </div>
        </div>
      )
    }

    if (verificationStatus?.verification.method.type === 'oauth') {
      return (
        <div className="space-y-6">
          <div className="text-center">
            <div className="flex flex-col items-center gap-4 mb-6">
              {verificationStatus?.guild_icon && (
                <div className="relative w-24 h-24">
                  <Image
                    src={verificationStatus.guild_icon}
                    alt={verificationStatus.guild_name}
                    fill
                    unoptimized
                    className="object-cover rounded-full"
                  />
                </div>
              )}
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {verificationStatus.guild_name}
                </h2>
                <h3 className="text-white/60 text-sm mt-1">
                  {verificationStatus.verification.method.name}
                </h3>
              </div>
            </div>
            
            <div className="space-y-6">
              <p className="text-white/60 text-sm">
                {verificationStatus.verification.method.description}
              </p>
              <button
                onClick={() => signIn('oauth', { 
                  callbackUrl: `/verify/${params.guildId}?session=${verificationSession?.session}` 
                })}
                className="w-full bg-[#d51007] hover:bg-[#b30d06] text-white font-medium 
                         py-3 px-4 rounded-lg transition-all duration-200 
                         flex items-center justify-center gap-2"
              >
                <FaLastfm className="h-5 w-5" />
                Connect with Last.fm
              </button>
            </div>
          </div>
        </div>
      )
    }
    
    if (verificationStatus?.verification.method.type === 'captcha') {
      return (
        <div className="space-y-6">
          <div className="text-center">
            <div className="flex flex-col items-center gap-4 mb-6">
              {verificationStatus?.guild_icon && (
                <div className="relative w-24 h-24">
                  <Image
                    src={verificationStatus.guild_icon}
                    alt={verificationStatus.guild_name}
                    fill
                    unoptimized
                    className="object-cover rounded-full"
                  />
                </div>
              )}
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {verificationStatus.guild_name}
                </h2>
                <h3 className="text-white/60 text-sm mt-1">
                  {verificationStatus.verification.method.name}
                </h3>
              </div>
            </div>
            
            {captchaStep === 1 ? (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <p className="text-white/60 text-sm">
                  {verificationStatus.verification.method.description}
                </p>
                <button
                  onClick={startCaptchaVerification}
                  className="w-full bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 
                           hover:border-white/10 text-white font-medium py-3 px-4 rounded-lg 
                           transition-all duration-200 flex items-center justify-center gap-2"
                >
                  Start Verification
                </button>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <p className="text-white/60 text-sm">
                  Complete the CAPTCHA below to verify your account
                </p>
                <div className="flex justify-center">
                  <HCaptcha
                    ref={captchaRef}
                    sitekey={process.env.NEXT_PUBLIC_HCAPTCHA_SITE_KEY!}
                    onVerify={handleCaptchaVerify}
                    theme="dark"
                  />
                </div>
                <button
                  onClick={() => setCaptchaStep(1)}
                  className="text-white/40 hover:text-white/60 text-sm transition-colors"
                >
                  ← Go back
                </button>
              </motion.div>
            )}
          </div>
        </div>
      )
    }
    
    return (
      <div className="text-center">
        <div className="flex flex-col items-center gap-4 mb-6">
          {verificationStatus?.guild_icon && (
            <div className="relative w-24 h-24">
              <Image
                src={verificationStatus?.guild_icon}
                alt={verificationStatus?.guild_name}
                fill
                unoptimized
                className="object-cover rounded-full"
              />
            </div>
          )}
          <div>
            <h2 className="text-2xl font-bold text-white">
              {verificationStatus?.guild_name}
            </h2>
            <h3 className="text-white/60 text-sm mt-1">
              {verificationStatus?.verification.method.name}
            </h3>
          </div>
        </div>
        
        <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6 mb-8">
          <p className="text-white/60">
            {verificationStatus?.verification.method.description}
          </p>
        </div>

        {!verificationSession ? (
          <button
            onClick={startVerification}
            disabled={sendingEmail}
            className="w-full bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 
                     hover:border-white/10 text-white font-medium py-3 px-4 rounded-lg 
                     transition-all duration-200 flex items-center justify-center gap-2 
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sendingEmail ? (
              <>
                <div className="w-4 h-4 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
                <span>Sending Email...</span>
              </>
            ) : (
              'Start Verification'
            )}
          </button>
        ) : (
          <div className="space-y-4">
            {emailSent && (
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-green-200 mb-4">
                Verification email has been sent. Please check your inbox.
              </div>
            )}
            <input
              type="text"
              placeholder="Enter verification code"
              value={emailCode}
              onChange={(e) => setEmailCode(e.target.value)}
              className="w-full bg-white/[0.02] border border-white/5 rounded-lg px-4 py-3 
                       text-white placeholder:text-white/40 focus:outline-none 
                       focus:border-white/20 transition-colors"
            />
            <button
              onClick={submitVerification}
              className="w-full bg-white/10 hover:bg-white/15 text-white font-medium 
                       py-3 px-4 rounded-lg transition-colors"
            >
              Submit Verification
            </button>
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white/60" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center p-4">
      <div className="absolute inset-0 bg-[url('/noise.png')] opacity-5" />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative max-w-md w-full space-y-8 bg-white/[0.02] border border-white/5 p-8 rounded-xl"
      >
        {error === ERROR_MESSAGES.ALREADY_VERIFIED ? (
          <div className="text-center">
            <div className="flex flex-col items-center gap-6">
              <div className="relative w-24 h-24 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                <svg 
                  className="w-12 h-12 text-blue-500" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" 
                  />
                </svg>
              </div>
              
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">
                  Already Verified
                </h2>
                <p className="text-white/60 text-sm max-w-sm">
                  You are already verified in {verificationStatus?.guild_name}. No further action is needed.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 mt-4">
                <a
                  href="/"
                  className="px-6 py-2 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 
                           hover:border-white/10 rounded-lg text-white transition-all duration-200 
                           flex items-center justify-center gap-2"
                >
                  Return Home
                </a>
                <a
                  href="https://discord.com"
                  className="px-6 py-2 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 
                           hover:border-white/10 rounded-lg text-white transition-all duration-200 
                           flex items-center justify-center gap-2"
                >
                  Open Discord
                </a>
              </div>
            </div>
          </div>
        ) : error ? (
          <div className="text-center">
            <div className="flex flex-col items-center gap-6">
              <div className="relative w-24 h-24 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                <svg 
                  className="w-12 h-12 text-red-500" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
                  />
                </svg>
              </div>
              
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">
                  Verification Error
                </h2>
                <p className="text-white/60 text-sm max-w-sm">
                  {error}
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 mt-4">
                <button
                  onClick={() => {
                    setError(null)
                    setVerificationSession(null)
                    setEmailCode('')
                    setEmailSent(false)
                  }}
                  className="px-6 py-2 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 
                           hover:border-white/10 rounded-lg text-white transition-all duration-200 
                           flex items-center justify-center gap-2"
                >
                  Try Again
                </button>
                <a
                  href="/"
                  className="px-6 py-2 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 
                           hover:border-white/10 rounded-lg text-white transition-all duration-200 
                           flex items-center justify-center gap-2"
                >
                  Return Home
                </a>
              </div>
            </div>
          </div>
        ) : isPendingReview ? (
          <div className="text-center space-y-4">
            <h3 className="text-xl font-semibold text-white">Answers Submitted</h3>
            <p className="text-white/60">
              Your answers have been submitted and are pending review by server moderators.
              You will be notified once your verification is approved.
            </p>
          </div>
        ) : isVerified ? (
          <div className="text-center">
            <div className="flex flex-col items-center gap-6">
              <div className="relative w-24 h-24 rounded-full bg-green-500/10 border border-green-500/20 flex items-center justify-center">
                <svg 
                  className="w-12 h-12 text-green-500" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M5 13l4 4L19 7" 
                  />
                </svg>
              </div>
              
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">
                  Verification Successful
                </h2>
                <p className="text-white/60 text-sm max-w-sm">
                  You have successfully verified your account for {verificationStatus?.guild_name}. You can now return to Discord.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 mt-4">
                <a
                  href="/"
                  className="px-6 py-2 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 
                           hover:border-white/10 rounded-lg text-white transition-all duration-200 
                           flex items-center justify-center gap-2"
                >
                  Return Home
                </a>
                <a
                  href="https://discord.com"
                  className="px-6 py-2 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 
                           hover:border-white/10 rounded-lg text-white transition-all duration-200 
                           flex items-center justify-center gap-2"
                >
                  Open Discord
                </a>
              </div>
            </div>
          </div>
        ) : verificationStatus && (
          renderVerificationMethod()
        )}
      </motion.div>
    </div>
  )
}