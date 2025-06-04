import "@/styles/globals.css"
import type { Metadata, Viewport } from "next"

export const viewport: Viewport = {
    themeColor: "transparent"
}

export const metadata: Metadata = {
    title: "coffin",
    description: "The only aesthetic multi-functional discord bot you need.",
    twitter: {
        site: "https://coffin.bot/",
        card: "player"
    },
    openGraph: {
        url: "https://coffin.bot/",
        type: "website",
        title: "coffin",
        siteName: "coffin.bot",
        description: "The only aesthetic multi-functional discord bot you need.",
        images: [
            {
                url: "https://cdn.coffin.bot/coffin.png",
                width: 500,
                height: 500,
                alt: "coffin"
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
                {children}
            </body>
        </html>
    )
}
