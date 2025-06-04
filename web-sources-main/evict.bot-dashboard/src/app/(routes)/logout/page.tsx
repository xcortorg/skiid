"use client"

import { auth } from "@/auth"
import { signOut } from "next-auth/react"
import { Session } from "next-auth"
import { useEffect, useState } from "react"

export default function Logout() {
    const [session, setSession] = useState<Session | null>(null)

    useEffect(() => {
        const fetchSession = async () => {
            const session = await auth()
            setSession(session)
        }

        fetchSession()
    }, [])

    if (!session) {
        return (
            <main className="flex items-center justify-center flex-col pb-20 pt-20">
                <div className="flex flex-col mx-10 items-center text-center justify-center sm:mx-0">
                    <h1>You are not logged in.</h1>
                </div>
            </main>
        )
    }

    return (
        <main className="flex items-center justify-center flex-col pb-20 pt-20">
            <div className="flex flex-col mx-10 items-center text-center justify-center sm:mx-0">
                <form
                    onSubmit={async e => {
                        e.preventDefault()
                        await signOut({ callbackUrl: "/" })
                    }}>
                    <button type="submit">Logout</button>
                </form>
            </div>
        </main>
    )
}
