import { auth } from "@/auth"
import { redirect } from "next/navigation"

export default async function ConnectedPage() {
    const session = await auth()
    if (!session) redirect("/login")

    return (
        <main className="flex h-[calc(100vh-12rem)] items-center justify-center">
            <div className="w-full max-w-md rounded-xl bg-zinc-900/30 p-8 backdrop-blur-sm border border-zinc-800/50 shadow-[0_0_15px_rgba(0,0,0,0.2)]">
                <div className="mb-6">
                    <div className="h-16 w-16 bg-[#5865F2] rounded-full mx-auto flex items-center justify-center shadow-[0_0_15px_rgba(88,101,242,0.3)]">
                        <svg className="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                </div>
                <div className="text-center">
                    <h1 className="text-2xl font-semibold tracking-tight text-zinc-100 mb-3">Successfully Connected!</h1>
                    <p className="text-zinc-400 text-sm mb-6">Your account has been successfully linked.</p>
                    <div className="space-y-3">
                        <a 
                            href="/login"
                            className="block w-full bg-zinc-800/50 text-zinc-200 px-6 py-2.5 rounded-lg hover:bg-zinc-800/70 transition-all focus:ring-2 focus:ring-zinc-700 focus:ring-offset-2 focus:ring-offset-black text-sm font-medium border border-zinc-700/50"
                        >
                            Manage Logins
                        </a>
                        <a 
                            href="/"
                            className="block w-full bg-zinc-900/50 text-zinc-400 px-6 py-2.5 rounded-lg hover:bg-zinc-800/50 transition-all focus:ring-2 focus:ring-zinc-700 focus:ring-offset-2 focus:ring-offset-black text-sm font-medium border border-zinc-800/50"
                        >
                            Return Home
                        </a>
                    </div>
                </div>
            </div>
        </main>
    )
}