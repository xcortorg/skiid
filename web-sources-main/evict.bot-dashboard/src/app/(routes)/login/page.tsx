"use client"

import { signIn, signOut, useSession } from "next-auth/react"
import { useSearchParams } from "next/navigation"
import { FaDiscord, FaLastfm } from "react-icons/fa" // Removed FaSpotify
import { IoLockClosed, IoCheckmarkCircle } from "react-icons/io5"
import { Session } from "next-auth"

export default function Login() {
    const { data: session } = useSession() as { data: Session | null }
    const searchParams = useSearchParams()
    const redirect = searchParams.get("redirect")
    // const forSpotify = searchParams.get("forSpotify") === "true" // Commented out
    const forLastfm = searchParams.get("forLastfm") === "true"
    const forBeta = searchParams.get("forBeta") === "true"
    const redirectTo = forBeta ? "/beta" : (/*forSpotify ||*/ forLastfm ? "/login" : (redirect || "/"))

    const handleSignIn = async (provider: "discord" | /*"spotify" |*/ "lastfm") => {
        if (provider === "discord") {
            const callbackUrl = redirect || (forBeta ? "/beta" : 
                (/*forSpotify ||*/ forLastfm ? "/login?" + searchParams.toString() : "/"))
            await signIn(provider, { callbackUrl })
        } else {
            await signIn(provider, { callbackUrl: redirectTo })
        }
    }

    return (
        <main className="flex min-h-[80vh] items-center justify-center">
            <div className="w-full max-w-md space-y-8 rounded-xl bg-zinc-900/50 p-8 shadow-xl backdrop-blur-sm">
                {!session ? (
                    <>
                        <div className="text-center">
                            <h2 className="text-3xl font-bold tracking-tight text-zinc-100">
                                Welcome back
                            </h2>
                            <p className="mt-2 text-sm text-zinc-400">
                                Sign in with Discord first to access all features
                            </p>
                        </div>

                        <div className="mt-8 space-y-6">
                            <button
                                onClick={() => handleSignIn("discord")}
                                className="flex w-full items-center justify-center gap-3 rounded-lg bg-[#5865F2] px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-[#4752C4] focus:ring-2 focus:ring-[#5865F2] focus:ring-offset-2 focus:ring-offset-zinc-900">
                                <FaDiscord className="h-5 w-5" />
                                Continue with Discord
                            </button>

                            <div className="space-y-2">
                                <div className="relative flex items-center">
                                    <div className="flex-grow border-t border-zinc-700"></div>
                                    <span className="mx-4 flex-shrink text-xs text-zinc-500">AFTER DISCORD LOGIN</span>
                                    <div className="flex-grow border-t border-zinc-700"></div>
                                </div>

                                {/* <button
                                    disabled={!session}
                                    onClick={() => handleSignIn("spotify")}
                                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-800 px-4 py-3 text-sm font-semibold text-zinc-400 transition-all">
                                    <FaSpotify className="h-5 w-5" />
                                    <IoLockClosed className="h-4 w-4" />
                                    Connect Spotify
                                </button> */}

                                <button
                                    disabled={!session}
                                    onClick={() => handleSignIn("lastfm")}
                                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-800 px-4 py-3 text-sm font-semibold text-zinc-400 transition-all">
                                    <div className="flex items-center gap-2">
                                        <FaLastfm className="h-5 w-5" />
                                        <IoLockClosed className="h-4 w-4" />
                                    </div>
                                    Connect Last.fm
                                </button>
                            </div>
                        </div>

                        <p className="mt-6 text-center text-sm text-zinc-500">
                            By continuing, you agree to our Terms of Service and Privacy Policy
                        </p>
                    </>
                ) : /*forSpotify ||*/ forLastfm ? (
                    <>
                        <div className="text-center">
                            <h2 className="text-3xl font-bold tracking-tight text-zinc-100">
                                {/*forSpotify ? "Connect Spotify" :*/ "Connect Last.fm"}
                            </h2>
                            <p className="mt-2 text-sm text-zinc-400">
                                You&apos;re signed in with Discord. Connect your {/*forSpotify ? "Spotify" :*/ "Last.fm"} account to continue.
                            </p>
                        </div>

                        <div className="mt-8">
                            <button
                                onClick={() => handleSignIn(/*forSpotify ? "spotify" :*/ "lastfm")}
                                className={`flex w-full items-center justify-center gap-3 rounded-lg px-4 py-3 text-sm font-semibold text-white transition-all ${
                                    /*forSpotify 
                                        ? "bg-[#1DB954] hover:bg-[#1aa34a] focus:ring-2 focus:ring-[#1DB954] focus:ring-offset-2 focus:ring-offset-zinc-900"
                                        :*/ "bg-[#d51007] hover:bg-[#b30d06] focus:ring-2 focus:ring-[#d51007] focus:ring-offset-2 focus:ring-offset-zinc-900"
                                }`}>
                                {/*forSpotify ? <FaSpotify className="h-5 w-5" /> :*/ <FaLastfm className="h-5 w-5" />}
                                Connect {/*forSpotify ? "Spotify" :*/ "Last.fm"}
                            </button>
                        </div>

                        <p className="mt-6 text-center text-sm text-zinc-500">
                            This will allow us to access your {/*forSpotify ? "Spotify" :*/ "Last.fm"} data
                        </p>
                    </>
                ) : (
                    <>
                        <div className="text-center">
                            <h2 className="text-3xl font-bold tracking-tight text-zinc-100">
                                Account Connected
                            </h2>
                            <p className="mt-2 text-sm text-zinc-400">
                                Manage your connected accounts
                            </p>
                        </div>

                        <div className="mt-8 space-y-3">
                            <button
                                onClick={() => signOut()}
                                className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5865F2] px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-[#4752C4] focus:ring-2 focus:ring-[#5865F2] focus:ring-offset-2 focus:ring-offset-zinc-900">
                                <FaDiscord className="h-5 w-5" />
                                Connected with Discord
                                <IoCheckmarkCircle className="h-5 w-5 ml-1" />
                            </button>

                            {/* <button
                                onClick={() => handleSignIn("spotify")}
                                className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#1DB954] px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-[#1aa34a] focus:ring-2 focus:ring-[#1DB954] focus:ring-offset-2 focus:ring-offset-zinc-900">
                                <FaSpotify className="h-5 w-5" />
                                {session.spotify ? "Connect Spotify" : "Connect Spotify"}
                                {session.spotify ? <IoCheckmarkCircle className="h-5 w-5 ml-1" /> : <IoLockClosed className="h-4 w-4 ml-1" />}
                            </button> */}

                            <button
                                onClick={() => handleSignIn("lastfm")}
                                className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#d51007] px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-[#b30d06] focus:ring-2 focus:ring-[#d51007] focus:ring-offset-2 focus:ring-offset-zinc-900">
                                <FaLastfm className="h-5 w-5" />
                                {session.lastfm ? "Connect Last.fm" : "Connect Last.fm"}
                                {session.lastfm ? <IoCheckmarkCircle className="h-5 w-5 ml-1" /> : <IoLockClosed className="h-4 w-4 ml-1" />}
                            </button>
                        </div>

                        <p className="mt-6 text-center text-sm text-zinc-500">
                            You can disconnect services at any time
                        </p>
                    </>
                )}
            </div>
        </main>
    )
}