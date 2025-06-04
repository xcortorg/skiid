"use client"

import { useEffect, useState } from "react"
import { FaGithub, FaGlobe } from "react-icons/fa"
import { SiDiscord, SiSpotify } from "react-icons/si"
import Loading from "./../loading"

const apiKey = "a70c1ab9-2b72-4371-a3cb-a499f24f127f"

interface TeamMember {
    id: string
    role: "Developer" | "Head Staff" | "Staff"
    name: string
}

interface Donator {
    id: string
    tier: "Premium" | "Premium+" | "Ultimate"
}

interface Guild {
    tag: string | null
    identity_guild_id: string | null
    badge: string | null
    identity_enabled: boolean
}

interface AvatarDecoration {
    sku_id: number
    asset: string
    expires_at: number | null
}

interface Activity {
    flags: number
    id: string | null
    name: string
    type: number
    state: string | null
    details: string | null
    created_at: number
    timestamps: {
        start?: number
        end?: number
    }
    assets?: {
        large_image: string | null
        large_text: string | null
        small_image?: string | null
        small_text?: string | null
    } | null
    sync_id?: string
    party?: {
        id: string
    }
}

interface SpotifyData {
    timestamps: Record<string, number>
    album: string
    album_art_url: string
    artist: string
    song: string
    track_id: string
}

interface Links {
    github?: string
    discord?: string
    website?: string
    instagram?: string
    youtube?: string
}

interface DiscordUser {
    id: string
    username: string
    avatar: string
    discriminator: string
    clan: Guild
    avatar_decoration_data: AvatarDecoration | null
    bot: boolean
    global_name: string | null
    primary_guild: Guild
    display_name: string
    public_flags: number
    roles: string[]
    badges: string[]
    boost_info?: {
        boosting: boolean
        months: number
        since: string
    }
    links?: Links
}

interface UserData {
    kv: Record<string, unknown>
    discord_user: DiscordUser
    activities: Activity[]
    discord_status: string
    active_on_discord_web: boolean
    active_on_discord_desktop: boolean
    active_on_discord_mobile: boolean
    listening_to_spotify: boolean
    spotify: SpotifyData | null
}

interface ApiResponse {
    data: UserData[]
    success: boolean
}

function TeamMemberCard({ presenceData }: { presenceData: UserData }) {
    const statusColor = {
        online: "bg-green-500",
        idle: "bg-yellow-500",
        dnd: "bg-red-500",
        offline: "bg-gray-600"
    }[presenceData.discord_status ?? "offline"]

    const defaultAvatarIndex = parseInt(presenceData.discord_user.id.slice(-1)) % 5
    const avatarUrl = presenceData.discord_user.avatar
        ? /^[0-9]+$/.test(presenceData.discord_user.avatar)
            ? `https://cdn.discordapp.com/embed/avatars/${presenceData.discord_user.avatar}.png`
            : `https://cdn.discordapp.com/avatars/${presenceData.discord_user.id}/${presenceData.discord_user.avatar}.${presenceData.discord_user.avatar.startsWith("a_") ? "gif" : "png"}?size=128`
        : `https://cdn.discordapp.com/embed/avatars/${defaultAvatarIndex}.png`

    return (
        <div className="bg-evict-200 border border-evict-card-border rounded-xl p-5 flex flex-col h-full">
            <div className="flex-1 flex gap-3 mb-2">
                <div className="relative flex-shrink-0 self-start">
                    <img
                        src={avatarUrl}
                        alt={presenceData.discord_user.display_name}
                        className="h-12 w-12 rounded-full object-cover"
                        loading="lazy"
                    />
                    {presenceData.discord_status !== "offline" && (
                        <div
                            className={`absolute right-0 bottom-0 w-[12.5px] h-[12.5px] rounded-full ${statusColor} ring-[1px] ring-evict-200`}
                        />
                    )}
                </div>

                <div className="flex-1 min-w-0 flex flex-col gap-1 justify-center">
                    <div>
                        <div className="flex items-baseline gap-2">
                            <h3 className="text-base font-medium text-white truncate">
                                {presenceData.discord_user.display_name}
                            </h3>
                            <span className="text-xs text-white/40">
                                {presenceData.discord_user.roles.includes("1265473601755414528")
                                    ? "Developer"
                                    : presenceData.discord_user.roles.includes(
                                            "1323255508609663098"
                                        )
                                      ? "Trial Support"
                                      : "Staff"}
                            </span>
                        </div>

                        {presenceData.spotify && (
                            <div className="flex items-start gap-3">
                                <div className="flex-1 flex items-start gap-1.5 min-w-0">
                                    <SiSpotify className="h-3.5 w-3.5 text-[#1DB954] flex-shrink-0 mt-1" />
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-sm text-white/60 truncate">
                                            {presenceData.spotify.song}
                                        </span>
                                        <span className="text-xs text-white/40 truncate">
                                            {presenceData.spotify.artist}
                                        </span>
                                    </div>
                                </div>
                                {presenceData.spotify.album_art_url && (
                                    <img
                                        src={`https://${presenceData.spotify.album_art_url.replace("https://i.scdn.co/image///", "")}`}
                                        alt={`${presenceData.spotify.album} album art`}
                                        className="h-10 w-10 rounded-md object-cover flex-shrink-0"
                                    />
                                )}
                            </div>
                        )}

                        {presenceData.activities.find(a => a.type === 4)?.state &&
                            !presenceData.spotify && (
                                <div className="text-sm text-white/40 italic">
                                    {presenceData.activities.find(a => a.type === 4)?.state}
                                </div>
                            )}
                    </div>
                </div>
            </div>

            <div className="flex gap-2 mt-auto pt-3 border-t border-white/5">
                {presenceData.discord_user.links?.github ? (
                    <a
                        href={presenceData.discord_user.links.github}
                        className="text-white/30 hover:text-white/60 transition-colors"
                        target="_blank"
                        rel="noopener noreferrer">
                        <FaGithub className="h-4 w-4" />
                    </a>
                ) : (
                    <span className="text-white/10 cursor-not-allowed">
                        <FaGithub className="h-4 w-4" />
                    </span>
                )}
                {presenceData.discord_user.links?.discord ? (
                    <a
                        href={presenceData.discord_user.links.discord}
                        className="text-white/30 hover:text-white/60 transition-colors"
                        target="_blank"
                        rel="noopener noreferrer">
                        <SiDiscord className="h-4 w-4" />
                    </a>
                ) : (
                    <span className="text-white/10 cursor-not-allowed">
                        <SiDiscord className="h-4 w-4" />
                    </span>
                )}
                {presenceData.discord_user.links?.website ? (
                    <a
                        href={presenceData.discord_user.links.website}
                        className="text-white/30 hover:text-white/60 transition-colors"
                        target="_blank"
                        rel="noopener noreferrer">
                        <FaGlobe className="h-4 w-4" />
                    </a>
                ) : (
                    <span className="text-white/10 cursor-not-allowed">
                        <FaGlobe className="h-4 w-4" />
                    </span>
                )}
            </div>
        </div>
    )
}

export default function TeamPage() {
    const [users, setUsers] = useState<ApiResponse["data"]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const headers: HeadersInit = { Authorization: apiKey }
        fetch("https://api.evict.bot/users/presence", { headers })
            .then(res => res.json())
            .then((data: ApiResponse) => {
                const uniqueUsers = data.data.filter(
                    (user, index, self) =>
                        index === self.findIndex(u => u.discord_user.id === user.discord_user.id)
                )
                setUsers(uniqueUsers)
                setLoading(false)
            })
    }, [])

    const developers = users.filter(u => u.discord_user.roles.includes("1265473601755414528"))
    const staff = users.filter(
        u =>
            (u.discord_user.roles.includes("1264110559989862406") ||
                u.discord_user.roles.includes("1323255508609663098")) &&
            !u.discord_user.roles.includes("1265473601755414528") &&
            u.discord_user.id !== "1305791169237876836" &&
            u.discord_user.id !== "617037497574359050"
    )

    if (loading) return <Loading />

    return (
        <div className="min-h-screen bg-[#0A0A0B]">
            <div className="relative border-b border-white/5 bg-black/20">
                <div className="absolute inset-0 top-0 bg-[url('/noise.png')] opacity-5" />
                <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-12 pt-24 relative">
                    <div className="text-center">
                        <span className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 md:mb-6 bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block">
                            Our Team
                        </span>
                        <p className="text-white/60 mt-4 text-base sm:text-lg max-w-3xl mx-auto">
                            Meet the people behind the project
                        </p>
                    </div>
                </div>
            </div>

            <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-8">
                <div className="mb-12">
                    <h2 className="text-2xl font-bold text-white text-center mb-2">Developers</h2>
                    <p className="text-white/60 text-center mb-8">
                        The core development team behind Evict
                    </p>
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                        {developers.map(user => (
                            <TeamMemberCard key={user.discord_user.id} presenceData={user} />
                        ))}
                    </div>
                </div>

                <div className="mb-12">
                    <h2 className="text-2xl font-bold text-white text-center mb-2">Staff</h2>
                    <p className="text-white/60 text-center mb-8">
                        Our dedicated support and moderation team
                    </p>
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                        {staff.map(user => (
                            <TeamMemberCard key={user.discord_user.id} presenceData={user} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
