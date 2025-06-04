import "@/styles/globals.css"
import type { Metadata, Viewport } from "next"
import { Manrope } from "next/font/google"
import { SessionProvider } from "next-auth/react"
import { AuthProvider } from '@/components/AuthProvider'
import { headers } from 'next/headers'

export const viewport: Viewport = {
    themeColor: "transparent"
}

export const metadata: Metadata = {
    title: "evict",
    description: "The only aesthetic multi-functional Discord bot you need.",
    twitter: {
        site: "https://evict.bot/",
        card: "player"
    },
    openGraph: {
        url: "https://evict.bot/",
        type: "website",
        title: "evict",
        siteName: "evict.bot",
        description: "The only aesthetic multi-functional Discord bot you need.",
        images: [
            {
                url: "https://r2.evict.bot/evict-new.png",
                width: 500,
                height: 500,
                alt: "evict"
            }
        ]
    }
}

export default function RootLayout({
    children
}: Readonly<{
    children: React.ReactNode
}>) {
    const headersList = headers()
    const pathname = headersList.get("x-pathname") || ""
    
    if (pathname.startsWith('/dashboard')) {
        <html lang="en" className="bg-black">
            <body className={`font-satoshi flex flex-col min-h-screen justify-between bg-gradient-to-b from-zinc-900 to-black`}>
                        {children}
            </body>
        </html>
    }

    return (
        <html lang="en" className="bg-black">
            <body className={`font-satoshi flex flex-col min-h-screen justify-between bg-gradient-to-b from-zinc-900 to-black`}>
                <SessionProvider>
                    <AuthProvider>
                        {children}
                    </AuthProvider>
                </SessionProvider>
            </body>
        </html>
    )
}