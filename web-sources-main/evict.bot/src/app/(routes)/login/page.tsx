"use client"

import { AnimatePresence, motion } from "framer-motion"
import { Session } from "next-auth"
import { signIn, signOut, useSession } from "next-auth/react"
import Image from "next/image"
import { useSearchParams } from "next/navigation"
import { FaDiscord, FaLastfm, FaSpotify } from "react-icons/fa"
import { IoCheckmarkCircle, IoLockClosed } from "react-icons/io5"

export default function Login() {
    const { data: session } = useSession() as { data: Session | null }
    const searchParams = useSearchParams()
    const redirect = searchParams.get("redirect")
    const forSpotify = searchParams.get("forSpotify") === "true"
    const forLastfm = searchParams.get("forLastfm") === "true"
    const forBeta = searchParams.get("forBeta") === "true"
    const redirectTo = forBeta ? "/beta" : forSpotify || forLastfm ? "/login" : redirect || "/"

    const handleSignIn = async (provider: "discord" | "spotify" | "lastfm") => {
        if (provider === "discord") {
            const callbackUrl =
                redirect ||
                (forBeta
                    ? "/beta"
                    : forSpotify || forLastfm
                      ? "/login?" + searchParams.toString()
                      : "/")
            await signIn(provider, { callbackUrl })
        } else {
            await signIn(provider, { callbackUrl: redirectTo })
        }
    }

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1,
                delayChildren: 0.3
            }
        }
    }

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: {
            opacity: 1,
            y: 0,
            transition: {
                duration: 0.5,
                ease: "easeOut"
            }
        }
    }

    return (
        <AnimatePresence mode="wait">
            <motion.main
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="relative min-h-screen flex items-center justify-center overflow-hidden">
                <motion.div
                    className="fixed inset-0 z-0 pointer-events-none opacity-[0.015] bg-noise"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0.015 }}
                    transition={{ duration: 1 }}
                />
                <motion.div
                    className="fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-white/5 via-transparent to-zinc-400/5 mix-blend-overlay"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 1 }}
                />

                <motion.div
                    variants={container}
                    initial="hidden"
                    animate="show"
                    className="w-full max-w-md relative z-10">
                    <motion.div
                        variants={item}
                        className="w-full space-y-8 rounded-3xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 p-8 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                        {!session ? (
                            <>
                                <motion.div variants={item} className="text-center">
                                    <Image
                                        src="https://r2.evict.bot/evict-new.png"
                                        alt="Evict"
                                        width={80}
                                        height={80}
                                        className="mx-auto mb-6 drop-shadow-2xl rounded-2xl brightness-100 [filter:_brightness(1)_sepia(0.1)_saturate(1.65)_hue-rotate(220deg)]"
                                    />
                                    <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent">
                                        Welcome back
                                    </h2>
                                    <p className="mt-2 text-sm text-zinc-400">
                                        Sign in with Discord first to access all features
                                    </p>
                                </motion.div>

                                <motion.div variants={item} className="mt-8 space-y-6">
                                    <motion.button
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        onClick={() => handleSignIn("discord")}
                                        className="flex w-full items-center justify-center gap-3 rounded-xl bg-[#5865F2] px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-[#4752C4] focus:ring-2 focus:ring-[#5865F2] focus:ring-offset-2 focus:ring-offset-zinc-900">
                                        <FaDiscord className="h-5 w-5" />
                                        Continue with Discord
                                    </motion.button>

                                    <div className="space-y-2">
                                        <div className="relative flex items-center">
                                            <div className="flex-grow border-t border-white/5"></div>
                                            <span className="mx-4 flex-shrink text-xs text-zinc-500">
                                                AFTER DISCORD LOGIN
                                            </span>
                                            <div className="flex-grow border-t border-white/5"></div>
                                        </div>

                                        <motion.button
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                            disabled={!session}
                                            onClick={() => handleSignIn("spotify")}
                                            className="flex w-full items-center justify-center gap-2 rounded-xl bg-white/[0.02] px-4 py-3 text-sm font-semibold text-zinc-400 transition-all border border-white/[0.05] hover:bg-white/[0.04]">
                                            <FaSpotify className="h-5 w-5" />
                                            <IoLockClosed className="h-4 w-4" />
                                            Connect Spotify
                                        </motion.button>

                                        <motion.button
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                            disabled={!session}
                                            onClick={() => handleSignIn("lastfm")}
                                            className="flex w-full items-center justify-center gap-2 rounded-xl bg-white/[0.02] px-4 py-3 text-sm font-semibold text-zinc-400 transition-all border border-white/[0.05] hover:bg-white/[0.04]">
                                            <div className="flex items-center gap-2">
                                                <FaLastfm className="h-5 w-5" />
                                                <IoLockClosed className="h-4 w-4" />
                                            </div>
                                            Connect Last.fm
                                        </motion.button>
                                    </div>
                                </motion.div>

                                <motion.p
                                    variants={item}
                                    className="mt-6 text-center text-sm text-zinc-500">
                                    By continuing, you agree to our Terms of Service and Privacy
                                    Policy
                                </motion.p>
                            </>
                        ) : forSpotify || forLastfm ? (
                            <>
                                <motion.div variants={item} className="text-center">
                                    <Image
                                        src="https://r2.evict.bot/evict-new.png"
                                        alt="Evict"
                                        width={80}
                                        height={80}
                                        className="mx-auto mb-6 drop-shadow-2xl rounded-2xl brightness-100 [filter:_brightness(1)_sepia(0.1)_saturate(1.65)_hue-rotate(220deg)]"
                                    />
                                    <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent">
                                        {forSpotify ? "Connect Spotify" : "Connect Last.fm"}
                                    </h2>
                                    <p className="mt-2 text-sm text-zinc-400">
                                        You&apos;re signed in with Discord. Connect your{" "}
                                        {forSpotify ? "Spotify" : "Last.fm"} account to continue.
                                    </p>
                                </motion.div>

                                <motion.div variants={item} className="mt-8">
                                    <motion.button
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        onClick={() =>
                                            handleSignIn(forSpotify ? "spotify" : "lastfm")
                                        }
                                        className={`flex w-full items-center justify-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-white transition-all ${
                                            forSpotify
                                                ? "bg-[#1DB954] hover:bg-[#1aa34a] focus:ring-2 focus:ring-[#1DB954] focus:ring-offset-2 focus:ring-offset-zinc-900"
                                                : "bg-[#d51007] hover:bg-[#b30d06] focus:ring-2 focus:ring-[#d51007] focus:ring-offset-2 focus:ring-offset-zinc-900"
                                        }`}>
                                        {forSpotify ? (
                                            <FaSpotify className="h-5 w-5" />
                                        ) : (
                                            <FaLastfm className="h-5 w-5" />
                                        )}
                                        Connect {forSpotify ? "Spotify" : "Last.fm"}
                                    </motion.button>
                                </motion.div>

                                <motion.p
                                    variants={item}
                                    className="mt-6 text-center text-sm text-zinc-500">
                                    This will allow us to access your{" "}
                                    {forSpotify ? "Spotify" : "Last.fm"} data
                                </motion.p>
                            </>
                        ) : (
                            <>
                                <motion.div variants={item} className="text-center">
                                    <Image
                                        src="https://r2.evict.bot/evict-new.png"
                                        alt="Evict"
                                        width={80}
                                        height={80}
                                        className="mx-auto mb-6 drop-shadow-2xl rounded-2xl brightness-100 [filter:_brightness(1)_sepia(0.1)_saturate(1.65)_hue-rotate(220deg)]"
                                    />
                                    <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent">
                                        Account Connected
                                    </h2>
                                    <p className="mt-2 text-sm text-zinc-400">
                                        Manage your connected accounts
                                    </p>
                                </motion.div>

                                <motion.div variants={item} className="mt-8 space-y-3">
                                    <motion.button
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        onClick={() => signOut()}
                                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#5865F2] px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-[#4752C4] focus:ring-2 focus:ring-[#5865F2] focus:ring-offset-2 focus:ring-offset-zinc-900">
                                        <FaDiscord className="h-5 w-5" />
                                        Connected with Discord
                                        <IoCheckmarkCircle className="h-5 w-5 ml-1" />
                                    </motion.button>

                                    <motion.button
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        onClick={() => handleSignIn("spotify")}
                                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#1DB954] px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-[#1aa34a] focus:ring-2 focus:ring-[#1DB954] focus:ring-offset-2 focus:ring-offset-zinc-900">
                                        <FaSpotify className="h-5 w-5" />
                                        {session.spotify
                                            ? "Connected with Spotify"
                                            : "Connect Spotify"}
                                        {session.spotify ? (
                                            <IoCheckmarkCircle className="h-5 w-5 ml-1" />
                                        ) : (
                                            <IoLockClosed className="h-4 w-4 ml-1" />
                                        )}
                                    </motion.button>

                                    <motion.button
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        onClick={() => handleSignIn("lastfm")}
                                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#d51007] px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-[#b30d06] focus:ring-2 focus:ring-[#d51007] focus:ring-offset-2 focus:ring-offset-zinc-900">
                                        <FaLastfm className="h-5 w-5" />
                                        {session.lastfm
                                            ? "Connected with Last.fm"
                                            : "Connect Last.fm"}
                                        {session.lastfm ? (
                                            <IoCheckmarkCircle className="h-5 w-5 ml-1" />
                                        ) : (
                                            <IoLockClosed className="h-4 w-4 ml-1" />
                                        )}
                                    </motion.button>
                                </motion.div>

                                <motion.p
                                    variants={item}
                                    className="mt-6 text-center text-sm text-zinc-500">
                                    You can disconnect services at any time
                                </motion.p>
                            </>
                        )}
                    </motion.div>
                </motion.div>
            </motion.main>
        </AnimatePresence>
    )
}
