"use client"

import Loading from "@/app/(routes)/loading"
import { Footer } from "@/components/(global)/Footer"
import Navbar from "@/components/(global)/navbar/Navbar"
import { usePathname } from "next/navigation"
import { Suspense, useEffect, useState } from "react"

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
    const pathname = usePathname()
    const isDashboardPage = pathname?.startsWith("/dashboard")
    const isApplyPage = pathname?.startsWith("/apply")
    const isSlugPage = pathname?.startsWith("/@")
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsLoading(false)
        }, 2500)

        return () => clearTimeout(timer)
    }, [])

    useEffect(() => {
        if (pathname && document.readyState === "complete") {
            setIsLoading(true)
            const timer = setTimeout(() => {
                setIsLoading(false)
            }, 2500)

            return () => clearTimeout(timer)
        }
    }, [pathname])

    if (isDashboardPage) {
        return children
    }

    return (
        <div>
            {isLoading && <Loading />}
            <div className={isLoading ? "" : ""}>
                {isApplyPage || isSlugPage ? (
                    children
                ) : (
                    <>
                        <Navbar />
                        <Suspense>{children}</Suspense>
                        <Footer />
                    </>
                )}
            </div>
        </div>
    )
}
