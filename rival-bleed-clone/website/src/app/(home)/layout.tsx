import type { Metadata, Viewport } from "next"
import "../../styles/globals.css"


export const viewport: Viewport = {
    themeColor: "transparent"
}

export const metadata: Metadata = {
    title: "rival",
    description: "The only aesthetic multi-functional discord bot you need.",
    twitter: {
        site: "https://dev.rival.rocks/",
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
                url: "/api/avatar.png",
                width: 500,
                height: 500,
                alt: "bleed"
            }
        ]
    }
}

export default function bleedMain({
    children
}: Readonly<{
    children: React.ReactNode
}>) {
    return (
        <html lang="en">
            <body className={`bg-bleed-100 font-satoshi`}>{children}</body>
        </html>
    )
}
