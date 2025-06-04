"use client"

import { usePathname } from "next/navigation"
import { Footer } from "@/components/(global)/Footer"
import Navbar from "@/components/(global)/navbar/Navbar"
import { Suspense } from "react"
import Loading from "@/app/(routes)/loading"

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
    const pathname = usePathname()
    const isDashboardPage = pathname?.startsWith("/dashboard")
    const isApplyPage = pathname?.startsWith("/apply")
    const isSlugPage = pathname?.startsWith("/@")

    if (isDashboardPage) {
        return children
    }

    return (
        <div>
            {isApplyPage || isSlugPage ? (
                children
            ) : (
                <>
                    <Navbar />
                    <Suspense fallback={<Loading />}>{children}</Suspense>
                    <Footer />
                </>
            )}
        </div>
    )
}