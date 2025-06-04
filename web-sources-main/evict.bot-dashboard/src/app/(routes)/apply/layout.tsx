import type { Metadata } from 'next'
import Navbar from '@/components/(global)/navbar/Navbar'
import { Footer } from '@/components/(global)/Footer'

export const metadata: Metadata = {
    title: 'Join Our Team - Evict',
    description: 'Join Evict\'s team of innovators and help shape the future of Discord moderation. Apply for roles in beta testing, community support, and more.',
    openGraph: {
        title: 'Join the Evict Team',
        description: 'Turn your passion for community building into impact. Join our team of innovators and help create the next generation of Discord moderation tools.',
        images: [
            {
                url: 'https://r2.evict.bot/og.png',
                width: 1200,
                height: 630,
                alt: 'Join Evict Team'
            }
        ],
        type: 'website',
        url: 'https://evict.bot/apply'
    },
    twitter: {
        card: 'summary_large_image',
        title: 'Join the Evict Team',
        description: 'Turn your passion for community building into impact. Join our team of innovators and help create the next generation of Discord moderation tools.',
        images: ['https://r2.evict.bot/og.png'], 
    }
}

export default function BetaLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <>
            <Navbar />
            {children}
            <Footer />
        </>
    )
} 