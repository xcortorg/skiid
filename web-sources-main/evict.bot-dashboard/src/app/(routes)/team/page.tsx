"use client"

import { useEffect, useState } from "react"
import { FaGithub, FaGlobe } from "react-icons/fa"
import { SiDiscord } from "react-icons/si"
import Loading from "./../loading"

const apiKey = ""

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

const TEAM_MEMBERS: TeamMember[] = [
    { id: "930383131863842816", role: "Developer", name: "66adam" },
    { id: "1272545050102071460", role: "Developer", name: "aiofiles" },
    { id: "598125772754124823", role: "Developer", name: "x32u" },
    { id: "1130715311897858180", role: "Staff", name: "reallysw75t" },
    { id: "1294608415129075743", role: "Staff", name: "isuckatusernameslol" }
]

const DONATORS: Donator[] = [
    { id: "263742810509803530", tier: "Premium" },
    { id: "1317328837805084693", tier: "Premium" },
    { id: "1030691074932482068", tier: "Premium" }
]

const BADGE_MAPPING: Record<string, string> = {
    Active_Developer: "Active_Developer",
    Discord_Nitro: "Discordnitro",
    House_Balance: "HypeSquad_Balance",
    House_Bravery: "HypeSquad_Bravery",
    House_Brilliance: "HypeSquad_Brilliance",
    Nitro_Boost: "Evolving_badge_Nitro_1_months",
    Quest: "Questbadge"
}

function TeamMemberCard({ member, presenceData }: { member: TeamMember; presenceData: UserData }) {
    const statusColor = {
        online: "bg-green-500",
        idle: "bg-yellow-500",
        dnd: "bg-red-500",
        offline: "bg-gray-500"
    }[presenceData.discord_status ?? "offline"]

    return (
        <div className="relative overflow-hidden rounded-xl bg-zinc-900/50 px-8 py-6 backdrop-blur-sm ring-1 ring-transparent hover:ring-zinc-700/50 transition-all">
            <div className="flex items-center gap-4">
                <div className="relative">
                    <img
                        src={
                            presenceData.discord_user.avatar
                                ? `https://cdn.discordapp.com/avatars/${presenceData.discord_user.id}/${presenceData.discord_user.avatar}.${presenceData.discord_user.avatar.startsWith("a_") ? "gif" : "png"}?size=128`
                                : `https://cdn.discordapp.com/embed/avatars/1.png`
                        }
                        alt={presenceData.discord_user.display_name}
                        className="relative h-16 w-16 rounded-full ring-2 ring-zinc-700 object-cover"
                        style={{ aspectRatio: "1/1", zIndex: 1 }}
                    />
                    {presenceData.discord_user.avatar_decoration_data?.asset && (
                        <img
                            src={`https://cdn.discordapp.com/avatar-decoration-presets/${presenceData.discord_user.avatar_decoration_data.asset}.png?size=256&passthrough=true`}
                            alt=""
                            className="absolute -inset-0 w-full h-full scale-[1.2] pointer-events-none"
                            style={{ zIndex: 2 }}
                        />
                    )}
                    <div
                        className={`absolute bottom-0 right-0 h-4 w-4 rounded-full ${statusColor} ring-2 ring-zinc-900`}
                        style={{ zIndex: 3 }}
                    />
                </div>
                <div className="flex flex-col">
                    <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                        {presenceData.discord_user.display_name}
                        {[
                            ...(presenceData.discord_user.badges || []),
                            ...(["598125772754124823", "930383131863842816"].includes(
                                presenceData.discord_user.id
                            )
                                ? ["Questbadge"]
                                : []),
                            ...(presenceData.discord_user.id === "438691702430236672"
                                ? ["HypeSquad_Brilliance", "Discordnitro", "Nitro_Boost"]
                                : [])
                        ].map((badge, i) => {
                            const normalizedBadge = badge.includes("Booster")
                                ? "Nitro_Boost"
                                : badge
                            return (
                                <img
                                    key={i}
                                    src={`/badges/${BADGE_MAPPING[normalizedBadge] || normalizedBadge}.png`}
                                    alt={badge}
                                    className={`${
                                        badge.includes("Nitro")
                                            ? "w-5 h-5"
                                            : badge.includes("Quest")
                                                ? "w-5 h-5"
                                                : "w-4 h-4"
                                    } hover:bg-zinc-800 rounded transition-colors`}
                                />
                            )
                        })}
                    </h3>
                    <p className="text-sm text-zinc-400">
                        {presenceData.discord_user.roles.includes("1265473601755414528")
                            ? "Developer"
                            : presenceData.discord_user.roles.includes("1323255508609663098")
                              ? "Trial Support"
                              : "Staff"}
                    </p>
                    {presenceData.spotify && (
                        <p
                            className="mt-1 text-xs text-zinc-500 truncate max-w-[200px] cursor-help"
                            title={`${presenceData.spotify.song} by ${presenceData.spotify.artist}`}>
                            Listening to {presenceData.spotify.song} by{" "}
                            {presenceData.spotify.artist}
                        </p>
                    )}
                    {presenceData.activities?.find(a => a.name === "Visual Studio Code") && (
                        <p
                            className="mt-1 text-xs text-zinc-500 truncate max-w-[200px] cursor-help"
                            title={`${presenceData.activities.find(a => a.name === "Visual Studio Code")?.details}`}>
                            Editing{" "}
                            {presenceData.activities
                                .find(a => a.name === "Visual Studio Code")
                                ?.details?.replace("Editing ", "")}
                        </p>
                    )}
                </div>
            </div>
            <div className="mt-4 flex gap-2">
                <a
                    href={presenceData.discord_user.links?.github || "#"}
                    className="rounded-lg bg-zinc-800/50 p-2.5 text-zinc-400 transition-colors hover:bg-zinc-700/50 hover:text-zinc-100">
                    <FaGithub className="h-5 w-5" />
                </a>
                <a
                    href={presenceData.discord_user.links?.website || "#"}
                    className="rounded-lg bg-zinc-800/50 p-2.5 text-zinc-400 transition-colors hover:bg-zinc-700/50 hover:text-zinc-100">
                    <FaGlobe className="h-5 w-5" />
                </a>
            </div>
        </div>
    )
}

export default function TeamPage() {
    const [users, setUsers] = useState<ApiResponse["data"]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const headers: HeadersInit = { 'Authorization': apiKey }
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

    if (loading) {
        return <Loading />
    }

    return (
        <main className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
            <div className="text-center">
                <h1 className="text-4xl font-bold tracking-tight text-zinc-100">Our Team</h1>
                <p className="mt-4 text-lg text-zinc-400">Meet the people behind the project</p>
            </div>

            <div className="mt-16">
                <div className="text-center mb-8">
                    <h2 className="text-2xl font-bold text-zinc-100">Developers</h2>
                    <p className="mt-2 text-zinc-400">The core development team behind Evict</p>
                </div>
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {developers.map(user => (
                        <div
                            key={user.discord_user.id}
                            className="relative overflow-hidden rounded-xl bg-zinc-900/50 px-8 py-6 backdrop-blur-sm ring-1 ring-transparent hover:ring-zinc-700/50 transition-all hover:shadow-lg hover:shadow-zinc-900/20">
                            <div className="flex items-center gap-5">
                                <div className="relative">
                                    <img
                                        src={
                                            user.discord_user.avatar
                                                ? `https://cdn.discordapp.com/avatars/${user.discord_user.id}/${user.discord_user.avatar}.${user.discord_user.avatar.startsWith("a_") ? "gif" : "png"}?size=128`
                                                : `https://cdn.discordapp.com/embed/avatars/0.png`
                                        }
                                        alt={user.discord_user.display_name}
                                        className="relative h-16 w-16 rounded-full ring-2 ring-zinc-700 object-cover"
                                        style={{ aspectRatio: "1/1", zIndex: 1 }}
                                    />
                                    {user.discord_user.avatar_decoration_data?.asset && (
                                        <img
                                            src={`https://cdn.discordapp.com/avatar-decoration-presets/${user.discord_user.avatar_decoration_data.asset}.png?size=256&passthrough=true`}
                                            alt=""
                                            className="absolute -inset-0 w-full h-full scale-[1.2] pointer-events-none"
                                            style={{ zIndex: 2 }}
                                        />
                                    )}
                                    <div
                                        className={`absolute bottom-0 right-0 h-4 w-4 rounded-full ${user.discord_status === "online" ? "bg-green-500" : user.discord_status === "idle" ? "bg-yellow-500" : user.discord_status === "dnd" ? "bg-red-500" : "bg-gray-500"} ring-2 ring-zinc-900`}
                                        style={{ zIndex: 3 }}
                                    />
                                </div>
                                <div className="flex flex-col">
                                    <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                                        {user.discord_user.display_name}
                                        {[
                                            ...(user.discord_user.badges || []),
                                            ...(["598125772754124823", "930383131863842816"].includes(user.discord_user.id)
                                                ? ["Questbadge"]
                                                : []),
                                            ...(user.discord_user.id === "438691702430236672"
                                                ? ["Discordnitro", "Nitro_Boost", "HypeSquad_Brilliance"]
                                                : [])
                                        ].map((badge, i) => {
                                            const normalizedBadge = badge.includes("Booster")
                                                ? "Nitro_Boost"
                                                : badge
                                            return (
                                                <img
                                                    key={i}
                                                    src={`/badges/${BADGE_MAPPING[normalizedBadge] || normalizedBadge}.png`}
                                                    alt={badge}
                                                    className={`${
                                                        badge.includes("Nitro")
                                                            ? "w-5 h-5"
                                                            : badge.includes("Quest")
                                                                ? "w-5 h-5"
                                                                : "w-4 h-4"
                                                    } hover:bg-zinc-800 rounded transition-colors`}
                                                />
                                            )
                                        })}
                                    </h3>
                                    <p className="text-sm text-zinc-400">
                                        {user.discord_user.roles.includes("1265473601755414528")
                                            ? "Developer"
                                            : user.discord_user.roles.includes("1323255508609663098")
                                              ? "Trial Support"
                                              : "Staff"}
                                    </p>
                                    {user.spotify && (
                                        <p
                                            className="mt-1 text-xs text-zinc-500 truncate max-w-[200px] cursor-help"
                                            title={`${user.spotify.song} by ${user.spotify.artist}`}>
                                            Listening to {user.spotify.song} by{" "}
                                            {user.spotify.artist}
                                        </p>
                                    )}
                                    {user.activities?.find(
                                        a => a.name === "Visual Studio Code"
                                    ) && (
                                        <p
                                            className="mt-1 text-xs text-zinc-500 truncate max-w-[200px] cursor-help"
                                            title={`${user.activities.find(a => a.name === "Visual Studio Code")?.details}`}>
                                            Editing{" "}
                                            {user.activities
                                                .find(a => a.name === "Visual Studio Code")
                                                ?.details?.replace("Editing ", "")}
                                        </p>
                                    )}
                                </div>
                            </div>
                            <div className="mt-6 flex gap-2">
                                <a
                                    href={user.discord_user.links?.github || `/#}`}
                                    className="rounded-lg bg-zinc-800/50 p-2.5 text-zinc-400 transition-colors hover:bg-zinc-700/50 hover:text-zinc-100">
                                    <FaGithub className="h-5 w-5" />
                                </a>
                                {user.discord_user.links?.discord && (
                                    <a
                                        href={user.discord_user.links.discord}
                                        className="rounded-lg bg-zinc-800/50 p-2.5 text-zinc-400 transition-colors hover:bg-zinc-700/50 hover:text-zinc-100">
                                        <SiDiscord className="h-5 w-5" />
                                    </a>
                                )}
                                <a
                                    href={user.discord_user.links?.website || "#"}
                                    className="rounded-lg bg-zinc-800/50 p-2.5 text-zinc-400 transition-colors hover:bg-zinc-700/50 hover:text-zinc-100">
                                    <FaGlobe className="h-5 w-5" />
                                </a>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="mt-16">
                <div className="text-center mb-8">
                    <h2 className="text-2xl font-bold text-zinc-100">Staff</h2>
                    <p className="mt-2 text-zinc-400">Our dedicated support and moderation team</p>
                </div>
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {staff.map(user => (
                        <TeamMemberCard
                            key={user.discord_user.id}
                            member={{
                                id: user.discord_user.id,
                                name: user.discord_user.display_name || user.discord_user.username,
                                role: "Staff"
                            }}
                            presenceData={user}
                        />
                    ))}
                </div>
            </div>
        </main>
    )
}
