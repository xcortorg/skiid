import NextAuth, { type Session } from "next-auth"
import Discord from "next-auth/providers/discord"
import Spotify from "next-auth/providers/spotify"
import crypto from 'crypto'

declare module "next-auth" {
    interface User {
        id?: string
        accessToken?: string
        provider?: string
        userToken?: string
    }
    interface Session {
        user: {
            id?: string
            email?: string
            name?: string
            spotify?: boolean
            lastfm?: boolean
            userToken?: string
            warning?: string
        }
    }
    interface Account {
        userToken?: string
    }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
    providers: [
        Discord({
            clientId: process.env.AUTH_DISCORD_ID,
            clientSecret: process.env.AUTH_DISCORD_SECRET,
            authorization: "https://discord.com/api/oauth2/authorize?scope=identify+guilds+email"
        }),
        Spotify({
            clientId: process.env.AUTH_SPOTIFY_ID,
            clientSecret: process.env.AUTH_SPOTIFY_SECRET,
            authorization:
                "https://accounts.spotify.com/authorize?scope=user-read-email+user-read-private+user-read-playback-state+user-modify-playback-state+user-read-currently-playing+playlist-read-private+playlist-read-collaborative+user-library-modify"
        }),
        {
            id: "lastfm",
            name: "Last.fm",
            type: "oauth",
            issuer: "https://www.last.fm",
            authorization: `https://www.last.fm/api/auth?api_key=${process.env.LASTFM_API_KEY}`,
            token: {
                url: "https://ws.audioscrobbler.com/2.0",
                params: {
                    method: "auth.getSession",
                    api_key: process.env.LASTFM_API_KEY,
                    format: "json"
                },
                async request(context: any) {
                    console.log("Last.fm token context:", context)
                    const response = await fetch(`https://ws.audioscrobbler.com/2.0?method=auth.getSession&api_key=${process.env.LASTFM_API_KEY}&token=${context.params.code}&format=json`)
                    const data = await response.json()
                    console.log("Last.fm session data:", data)
                    return {
                        tokens: {
                            access_token: data.session?.key,
                            username: data.session?.name
                        }
                    }
                }
            },
            userinfo: {
                url: "https://ws.audioscrobbler.com/2.0",
                params: {
                    method: "user.getInfo",
                    api_key: process.env.LASTFM_API_KEY,
                    format: "json"
                }
            }
        }
    ],
    secret: process.env.AUTH_SECRET,
    trustHost: true,
    callbacks: {
        async signIn({ account, user, profile }) {
            if (account?.provider === "discord") {
                try {                    
                    const response = await fetch("https://api.evict.bot/login", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-Special-Auth": "fzx62lRok3h57XHccs4KWCRubruFKSXu",
                            Origin: "https://evict.bot"
                        },
                        body: JSON.stringify({
                            user_id: profile?.id ?? "",
                            access_token: account.access_token
                        })
                    })

                    const data = await response.json()

                    if (!response.ok) return false

                    account.userToken = data.token
                    return true
                } catch (error) {
                    console.error("Failed to create bot token:", error)
                    return false
                }
            }
            if (account?.provider === "spotify") {
                const discordSession = await auth()

                try {
                    if (!discordSession?.user?.id) {
                        console.error("No Discord user ID found in session")
                        return false
                    }

                    const numericId = discordSession.user.id

                    const response = await fetch("https://api.evict.bot/spotify/auth", {
                        method: "POST",
                        headers: {
                            Authorization: process.env.NOTHIDDEN_API_KEY ?? "",
                            "Content-Type": "application/json",
                            Origin: "https://evict.bot"
                        },
                        body: JSON.stringify({
                            user_id: discordSession.user.id,
                            spotify_access_token: account.access_token,
                            spotify_refresh_token: account.refresh_token,
                            expires_in: account.expires_in,
                            spotify_id: user.id
                        })
                    })

                    if (!response.ok) {
                        const errorData = await response.text()
                        console.error("API Error Details:", {
                            status: response.status,
                            statusText: response.statusText,
                            headers: Object.fromEntries(response.headers),
                            body: errorData
                        })
                        return false
                    }

                    return "/connected"
                } catch (error) {
                    console.error("Failed to send Spotify credentials:", {
                        error,
                        account: {
                            provider: account.provider,
                            type: account.type,
                            expiresIn: account.expires_in
                        },
                        user: {
                            id: user.id
                        }
                    })
                    return false
                }
            }
            return true
        },
        async jwt({ token, account, profile }: { token: any; account: any; profile?: any }) {
            if (account?.provider === "discord" && profile?.id) {
                token.discordId = profile.id
                token.userToken = account.userToken
            }
            if (account?.provider === "spotify") {
                token.spotifyToken = account.access_token
            }
            return token
        },
        async session({ session, token }: { session: Session; token: any }) {
            if (session.user) {
                session.user.id = token.discordId as string
                session.user.userToken = token.userToken
                session.user.warning = "DO NOT SHARE THIS TOKEN WITH ANYONE, WE ARE NOT RESPONSIBLE FOR ANYTHING YOU DO WITH IT"
            }
            return session
        }
    },
    session: {
        strategy: "jwt",
        maxAge: 30 * 24 * 60 * 60, 
        updateAge: 24 * 60 * 60, 
    },
    jwt: {
        maxAge: 30 * 24 * 60 * 60, 
    },
    cookies: {
        sessionToken: {
            name: process.env.NODE_ENV === 'production' ? '__Secure-next-auth.session-token' : 'next-auth.session-token',
            options: {
                httpOnly: true,
                sameSite: 'lax',
                path: '/',
                secure: process.env.NODE_ENV === 'production',
            }
        }
    }
})
