import "next-auth"

declare module "next-auth" {
    interface Session {
        user: User
        spotify?: boolean
        lastfm?: boolean
    }
} 