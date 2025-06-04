import { Footer } from "@/components/(global)/Footer"
import Navbar from "@/components/(global)/navbar/Navbar"
import "@/styles/globals.css"
import type { Metadata, Viewport } from "next"
import { Manrope } from "next/font/google"

const manrope = Manrope({ subsets: ["latin"] })

export const viewport: Viewport = {
    themeColor: "transparent"
}

export const metadata: Metadata = {
    title: "marly",
    description: "The only aesthetic multi-functional discord bot you need.",
    twitter: {
        site: "https://marly.bot/",
        card: "player"
    },
    openGraph: {
        url: "https://marly.bot/",
        type: "website",
        title: "marly",
        siteName: "marly.bot",
        description: "The only aesthetic multi-functional discord bot you need.",
        images: [
            {
                url: "https://r2.skunkk.xyz/marly.gif",
                width: 500,
                height: 500,
                alt: "marly"
            }
        ]
    }
}

export default function RootLayout({
    children
}: Readonly<{
    children: React.ReactNode
}>) {
    return (
        <html lang="en">
            <body className={`font-satoshi flex flex-col m-h-screen justify-between`}>
                <Navbar />
                {children}
                <Footer />
            </body>
        </html>
    )
}
