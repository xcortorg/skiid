"use client";

import Link from "next/link";
import { FaKey, FaShieldAlt, FaSpinner } from "react-icons/fa";
import { AuthButton } from "@/components/ui/auth-button";
import { useState, useEffect, useRef } from "react";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/toast-provider";
import { Turnstile } from "@/components/ui/turnstile";

export default function LoginPage() {
  const { toast } = useToast();
  const { data: session, status } = useSession();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [showTwoFactor, setShowTwoFactor] = useState(false);
  const [useBackupCode, setUseBackupCode] = useState(false);
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [isBlocked, setIsBlocked] = useState(false);
  const [blockTimer, setBlockTimer] = useState(0);
  const [turnstileToken, setTurnstileToken] = useState<string>("");
  const [showVerification, setShowVerification] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");
  const turnstileRef = useRef<any>(null);

  useEffect(() => {
    if (status === "authenticated") {
      router.push("/dashboard");
    }
  }, [status, router]);

  useEffect(() => {
    if (blockTimer > 0) {
      const timer = setTimeout(() => {
        setBlockTimer(blockTimer - 1);
        if (blockTimer - 1 <= 0) {
          setIsBlocked(false);
        }
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [blockTimer]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const checkRateLimit = async () => {
    try {
      const res = await fetch("/api/auth/rate-limit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: formData.email,
          ip: "client-side",
        }),
      });

      const data = await res.json();

      if (!res.ok && data.blocked) {
        setIsBlocked(true);
        setBlockTimer(data.remainingTime);
        toast({
          title: "Too many login attempts",
          description: "Please try again later",
          variant: "error",
        });
        return false;
      }

      return true;
    } catch (error) {
      // If it fails, let the login go ahead yh (#PBC #PLAYBOYCARTI)
      return true;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!turnstileToken) {
      toast({
        title: "Verification required",
        description: "Please complete the challenge",
        variant: "error",
      });
      return;
    }

    if (isBlocked) {
      toast({
        title: "Too many login attempts",
        description: `Please wait ${blockTimer} seconds`,
        variant: "error",
      });
      return;
    }

    const canProceed = await checkRateLimit();
    if (!canProceed) return;

    setIsLoading(true);

    try {
      const result = await signIn("credentials", {
        email: formData.email,
        password: formData.password,
        turnstileToken: turnstileToken,
        verified: showVerification ? "true" : "false",
        code: twoFactorCode,
        isBackupCode: useBackupCode ? "true" : "false",
        redirect: false,
      });

      if (result?.error) {
        turnstileRef.current?.reset();
        setTurnstileToken("");

        switch (result.error) {
          case "VERIFICATION_REQUIRED":
          case "AccessDenied":
            setShowVerification(true);
            break;
          case "2FA_REQUIRED":
            setShowVerification(false);
            setShowTwoFactor(true);
            break;
          default:
            toast({
              title: "Login failed",
              description: result.error,
              variant: "error",
            });
        }
      } else if (result?.ok) {
        router.push("/dashboard");
      }
    } catch (error) {
      console.error("Login error:", error);
      toast({
        title: "Login failed",
        description: "Something went wrong",
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTwoFactorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!turnstileToken) {
      toast({
        title: "Verification required",
        description: "Please complete the challenge",
        variant: "error",
      });
      return;
    }

    if (isBlocked) {
      toast({
        title: "Too many login attempts",
        description: `Please wait ${blockTimer} seconds`,
        variant: "error",
      });
      return;
    }

    const canProceed = await checkRateLimit();
    if (!canProceed) return;

    setIsLoading(true);

    try {
      const result = await signIn("credentials", {
        email: formData.email,
        password: formData.password,
        code: twoFactorCode,
        isBackupCode: useBackupCode ? "true" : "false",
        turnstileToken: turnstileToken,
        verified: "true",
        redirect: false,
      });

      if (result?.error) {
        turnstileRef.current?.reset();
        setTurnstileToken("");
        toast({
          title: "2FA failed",
          description: result.error,
          variant: "error",
        });
        return;
      }

      router.push("/dashboard");
    } catch (error) {
      console.error("2FA error:", error);
      toast({
        title: "2FA failed",
        description: "An error occurred",
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerificationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (!turnstileToken) {
        toast({
          title: "Verification required",
          description: "Please complete the challenge",
          variant: "error",
        });
        return;
      }

      const res = await fetch("/api/auth/verify-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: formData.email,
          code: verificationCode,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        toast({
          title: "Verification failed",
          description: data.error || "Invalid verification code",
          variant: "error",
        });
        return;
      }

      const result = await signIn("credentials", {
        email: formData.email,
        password: formData.password,
        turnstileToken: turnstileToken,
        verified: "true",
        redirect: false,
      });

      if (result?.error === "2FA_REQUIRED") {
        setShowVerification(false);
        setShowTwoFactor(true);
      } else if (result?.error) {
        toast({
          title: "Login failed",
          description: "Login failed after verification",
          variant: "error",
        });
      }
    } catch (error) {
      console.error("Verification error:", error);
      toast({
        title: "Verification failed",
        description: "An error occurred during verification",
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderBlockedMessage = () => {
    if (!isBlocked) return null;
    return (
      <div className="text-sm text-red-500 text-center mt-2">
        Too many attempts. Try again in {blockTimer} seconds
      </div>
    );
  };

  if (status === "loading" || status === "authenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <FaSpinner className="animate-spin text-4xl text-pink" />
      </div>
    );
  }

  if (showTwoFactor) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="relative w-full max-w-[400px] overflow-hidden rounded-lg border border-primary bg-darker p-8">
          <div className="absolute inset-0 bg-grid-white/5 [mask-image:radial-gradient(white,transparent_85%)]" />

          <div className="relative">
            <Link href="/" className="block mb-6">
              <h2 className="text-2xl font-bold">
                emogir<span className="text-[#ff3379] text-sm">.ls</span>
              </h2>
            </Link>

            <form
              className="flex flex-col gap-4"
              onSubmit={handleTwoFactorSubmit}
            >
              <div className="flex flex-col gap-2">
                <label className="text-sm opacity-80">
                  {useBackupCode ? "Backup Code" : "2FA Code"}
                </label>
                <input
                  type="text"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                  placeholder={useBackupCode ? "XXXX-XXXX-XXXX" : "000000"}
                  pattern={
                    useBackupCode
                      ? "[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}"
                      : "[0-9]{6}"
                  }
                  required
                />
              </div>

              <div className="flex justify-center">
                <Turnstile
                  ref={turnstileRef}
                  siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!}
                  onSuccess={setTurnstileToken}
                />
              </div>

              <AuthButton
                text="verify"
                icon={FaShieldAlt}
                isLoading={isLoading}
                className="mt-2"
              />

              <button
                type="button"
                onClick={() => setUseBackupCode(!useBackupCode)}
                className="text-sm text-pink hover:opacity-80 transition-opacity"
              >
                {useBackupCode
                  ? "Use 2FA code instead"
                  : "Use backup code instead"}
              </button>
            </form>
            {renderBlockedMessage()}
          </div>
        </div>
      </div>
    );
  }

  if (showVerification) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="relative w-full max-w-[400px] overflow-hidden rounded-lg border border-primary bg-darker p-8">
          <div className="absolute inset-0 bg-grid-white/5 [mask-image:radial-gradient(white,transparent_85%)]" />

          <div className="relative">
            <Link href="/" className="block mb-6">
              <h2 className="text-2xl font-bold">
                emogir<span className="text-[#ff3379] text-sm">.ls</span>
              </h2>
            </Link>

            <form
              className="flex flex-col gap-4"
              onSubmit={handleVerificationSubmit}
            >
              <div className="flex flex-col gap-2">
                <label className="text-sm opacity-80">Verification Code</label>
                <input
                  type="text"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                  placeholder="Enter 6-digit code"
                  pattern="[0-9]{6}"
                  required
                />
              </div>

              <p className="text-sm text-gray-400 text-center">
                Please check your email for a verification code
              </p>

              <div className="flex justify-center">
                <Turnstile
                  ref={turnstileRef}
                  siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!}
                  onSuccess={setTurnstileToken}
                />
              </div>

              <AuthButton
                text="verify"
                icon={FaShieldAlt}
                isLoading={isLoading}
                className="mt-2"
              />
            </form>
            {renderBlockedMessage()}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="relative w-full max-w-[400px] overflow-hidden rounded-lg border border-primary bg-darker p-8">
        <div className="absolute inset-0 bg-grid-white/5 [mask-image:radial-gradient(white,transparent_85%)]" />

        <div className="relative">
          <Link href="/" className="block mb-6">
            <h2 className="text-2xl font-bold">
              emogir<span className="text-[#ff3379] text-sm">.ls</span>
            </h2>
          </Link>

          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-2">
              <label className="text-sm opacity-80">Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                placeholder="your@email.com"
                required
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm opacity-80">Password</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className="bg-primary border border-[#1a1a1a] rounded px-4 py-2 focus:outline-none focus:border-pink"
                placeholder="••••••••"
                required
              />
            </div>

            <div className="flex justify-center">
              <Turnstile
                ref={turnstileRef}
                siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!}
                onSuccess={setTurnstileToken}
              />
            </div>

            <div className="flex justify-between items-center text-sm mt-2">
              <Link
                href="/register"
                className="text-pink hover:opacity-80 transition-opacity"
              >
                Register
              </Link>
              <Link
                href="/forgot-password"
                className="text-pink hover:opacity-80 transition-opacity"
              >
                Forgot Password?
              </Link>
            </div>

            <AuthButton
              text="login"
              icon={FaKey}
              isLoading={isLoading}
              className="mt-4"
            />
          </form>
          {renderBlockedMessage()}
        </div>
      </div>
    </div>
  );
}
