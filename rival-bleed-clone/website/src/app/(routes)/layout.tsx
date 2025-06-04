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
    title: "rival",
    description: "The only aesthetic multi-functional discord bot you need.",
    twitter: {
        site: "https://dev.rival.rocks",
        card: "player"
    },
    openGraph: {
        url: "https://dev.rival.rocks/",
        type: "website",
        title: "rival",
        siteName: "rival.rocks",
        description: "The only aesthetic multi-functional discord bot you need.",
        images: [
            {
                url: "/api/avatar",
                width: 500,
                height: 500,
                alt: "rival"
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
