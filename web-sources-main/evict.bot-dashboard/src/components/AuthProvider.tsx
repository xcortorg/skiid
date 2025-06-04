'use client'

import { useSession } from "next-auth/react"
import { useEffect } from "react"

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const { data: session } = useSession()

    useEffect(() => {
        if (session?.user) {
            localStorage.setItem('userToken', session.user.userToken || '')
            // @ts-ignore
            localStorage.setItem('userImage', session.user.image || '')
        } else {
            localStorage.removeItem('userToken')
            localStorage.removeItem('userImage')
        }
    }, [session?.user])

    return <>{children}</>
} 