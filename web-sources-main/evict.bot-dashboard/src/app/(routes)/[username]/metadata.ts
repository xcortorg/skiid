import { Metadata } from 'next'

export async function generateMetadata({ params }: { params: { username: string } }): Promise<Metadata> {
    try {
        const cleanUsername = decodeURIComponent(params.username).replace('@', '')
        const response = await fetch(`https://api.evict.bot/socials`, {
            headers: {
                "X-USER-ID": cleanUsername,
                "Authorization": ""
            }
        })
        const profile = await response.json()

        return {
            title: `@${profile.user.name}`,
            description: profile.bio ? profile.bio.slice(0, 160) : `View @${profile.user.name}'s profile on Evict`,
            openGraph: {
                title: `${profile.user.name} — Evict Profile`,
                description: profile.bio ? profile.bio.slice(0, 160) : `View @${profile.user.name}'s profile on Evict`,
                images: [
                    {
                        url: profile.profile_image || profile.user.avatar,
                        width: 1200,
                        height: 630,
                        alt: profile.user.name
                    }
                ]
            },
            twitter: {
                card: 'summary_large_image',
                title: `${profile.user.name}`,
                description: profile.bio ? profile.bio.slice(0, 160) : `View @${profile.user.name}'s profile on Evict`,
                images: [profile.profile_image || profile.user.avatar],
            }
        }
    } catch (error) {
        return {
            title: 'Profile — Evict',
            description: 'View profile on Evict'
        }
    }
} 