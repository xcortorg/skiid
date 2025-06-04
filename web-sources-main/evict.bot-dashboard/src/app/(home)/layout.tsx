import type { Metadata, Viewport } from "next"
import "../../styles/globals.css"
import Navbar from "@/components/(global)/navbar/Navbar"
import { Footer } from "@/components/(global)/Footer"

export const viewport: Viewport = {
    themeColor: "776dd4"
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

export default function evictMain({
    children
}: Readonly<{
    children: React.ReactNode
}>) {
    return (
        <html lang="en">
            <body className={`bg-evict-100 font-satoshi`}>
                <Navbar />
                {children}
                <Footer />
            </body>
        </html>
    )
}
