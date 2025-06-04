import { avatars } from "@/components/ticket"

export type Avatars = {
    blue: string
    gray: string
    green: string
    orange: string
    red: string
    [key: string]: string
}

export type Profile = {
    author?: string
    avatar?: string
    bot?: boolean
    roleColor?: string
}

export type DiscordMessageOptions = {
    avatars: Avatars
    defaultMode: "cozy" | "compact"
    defaultTheme: "dark" | "light"
    profiles: { [key: string]: Profile | undefined }
}

export default {
    avatars: {
        ...avatars,
        default: "https://cdn.discordapp.com/embed/avatars/0.png"
    },
    defaultMode: "cozy",
    defaultTheme: "dark",
    profiles: {}
} as DiscordMessageOptions
