"use client"

import { Dialog, DialogContent } from "@/components/dialog"
import { format } from "date-fns"
import { motion } from "framer-motion"
import {
    AlertTriangle,
    Gamepad2,
    Music,
    Pause,
    Play,
    Volume1,
    Volume2,
    VolumeX
} from "lucide-react"
import { useSession } from "next-auth/react"
import Image from "next/image"
import { useEffect, useRef, useState } from "react"
import {
    FaDiscord,
    FaGithub,
    FaGlobe,
    FaInstagram,
    FaPinterest,
    FaReddit,
    FaSnapchat,
    FaTiktok,
    FaTwitch,
    FaTwitter,
    FaYoutube
} from "react-icons/fa"
import { toast } from "sonner"

interface EmojiData {
    name: string
    id?: string
    url?: string | null
    unicode?: string
}

type Activity = {
    name: string
    type: string
    details: string
    details_emoji: string | null
    state: string
    state_emoji: string | null
    emoji: string | null
    application_id?: string
    large_image?: string
    small_image?: string
    large_text?: string
    small_text?: string
    album_cover_url?: string
    track_url?: string
    duration?: number
    start?: number
    end?: number
}

interface UserProfile {
    user: {
        id: string
        name: string
        avatar: string
        banner: string | null
        created_at: string
        avatar_decoration_data?: {
            asset: string
        }
    }
    colors: ProfileColors
    presence: {
        status: string
        activities: Activity[]
    }
    badges: string[]
    bio: string
    bio_emoji?: EmojiData
    friends: Array<{
        id: string
        name: string
        avatar: string
    }>
    links: Array<{
        type: string
        url: string
    }>
    background_url: string | null
    glass_effect: boolean
    discord_guild?: string
    click: {
        enabled: boolean
        text: string
    }
    audio?: {
        url: string
        title?: string
    }
    profile_color?: string
    gradient_colors?: Array<{
        color: string
        position: number
    }>
    linear_color?: string
}

interface DiscordGuild {
    id: string
    name: string
    icon: string
    member_count: number
    presence_count: number
    description?: string
}

const statusColors = {
    online: "bg-green-500",
    idle: "bg-yellow-500",
    dnd: "bg-red-500",
    offline: "bg-gray-500"
} as const

const badgeIcons = {
    support: "/badges/slug/support.png",
    trial: "/badges/slug/trial.png",
    mod: "/badges/slug/mod.png",
    donor1: "/badges/slug/donor1.png",
    donor4: "/badges/slug/donor4.png",
    staff: "/badges/slug/staff.png",
    developer: "/badges/slug/developer.png",
    owner: "/badges/slug/owner.png"
} as const

type BadgeType = keyof typeof badgeIcons

const badgeNames: Record<BadgeType, string> = {
    support: "Support Team",
    trial: "Trial Moderator",
    mod: "Moderator",
    donor1: "Donator",
    donor4: "Instance Owner",
    staff: "Staff Member",
    developer: "Developer",
    owner: "Owner"
}

const renderEmoji = (emoji?: EmojiData) => {
    if (!emoji) return ""

    if (emoji.url) {
        return `<img src="${emoji.url}" alt="${emoji.name}" class="inline-block w-5 h-5" />`
    }

    return emoji.unicode || emoji.name || ""
}

const urlPattern = /https?:\/\/[^\s<]+[^<.,:;"')\]\s]/g

async function formatDiscordText(text: string, colors: ProfileColors, username: string) {
    if (!text) return ""

    try {
        const response = await fetch(`/api/socials`, {
            method: "GET",
            headers: {
                "X-USER-ID": username
            }
        })

        if (!response.ok) {
            throw new Error("Failed to fetch original bio")
        }

        const data = await response.json()
        const originalBio = data.bio

        const firstLine = originalBio.split("\n")[0]
        const firstTwoWords = firstLine.match(/^(\S+\s+\S+)/)

        if (firstTwoWords) {
            text = text.replace(/^\S+\S+/, firstTwoWords[1])
        }
    } catch (error) {
        console.error("Failed to fetch original spacing:", error)
    }

    let formattedText = text
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"')
        .replace(/&(?!amp;|lt;|gt;|quot;)/g, "&amp;")

    formattedText = formattedText
        .replace(
            /\*\*(.*?)\*\*/g,
            `<strong style="color: ${getElementColor(colors, "bold_text")}">$1</strong>`
        )
        .replace(/\[(.*?)\]\((.*?)\)/g, (match, text, url) => {
            const cleanText = text.replace(/\*([^*]+)\*/g, "$1")
            return `<a href="javascript:void(0)" data-url="${url}" class="${colors.elements.text_underline.type === "linear" ? "text-blue-400 hover:underline" : ""}" style="${colors.elements.text_underline.type === "gradient" ? `border-bottom: 2px solid ${getElementColor(colors, "text_underline")}` : ""}" onclick="window.handleExternalLink(this)">${cleanText}</a>`
        })
        .replace(
            urlPattern,
            url =>
                `<a href="javascript:void(0)" data-url="${url}" class="text-blue-400 hover:underline" onclick="window.handleExternalLink(this)">${url}</a>`
        )

    return formattedText
}

const formatBio = (bio: string | null) => {
    if (!bio) return ""
    return bio.split("\n").slice(0, 10).join("\n")
}

const socialIcons = {
    instagram: FaInstagram,
    youtube: FaYoutube,
    github: FaGithub,
    discord: FaDiscord,
    twitter: FaTwitter,
    twitch: FaTwitch,
    reddit: FaReddit,
    pinterest: FaPinterest,
    snapchat: FaSnapchat,
    tiktok: FaTiktok
} as const

const extractInviteCode = (inviteUrl: string): string | null => {
    const patterns = [
        /discord\.gg\/([a-zA-Z0-9-]+)/,
        /discord\.com\/invite\/([a-zA-Z0-9-]+)/,
        /discordapp\.com\/invite\/([a-zA-Z0-9-]+)/,
        /^([a-zA-Z0-9-]+)$/
    ]

    for (const pattern of patterns) {
        const match = inviteUrl.match(pattern)
        if (match) return match[1]
    }

    return null
}

const fetchGuildData = async (guildId: string) => {
    try {
        const inviteCode = extractInviteCode(guildId)
        if (!inviteCode) throw new Error("Invalid invite URL")

        const response = await fetch(
            `https://discord.com/api/v9/invites/${inviteCode}?with_counts=true`
        )
        return await response.json()
    } catch (error) {
        console.error("Failed to fetch guild data:", error)
        return null
    }
}

const reportReasons = [
    "Explicit/NSFW Background",
    "Inappropriate Content",
    "Harassment/Bullying",
    "Impersonation",
    "Spam/Advertising",
    "Other"
] as const

const calculateRemaining = (start: number, end: number) => {
    const now = Date.now() / 1000
    const remaining = end - now
    return Math.max(0, remaining)
}

const calculateProgress = (start: number, end: number) => {
    const now = Date.now() / 1000
    const total = end - start
    const elapsed = now - start
    const progress = (elapsed / total) * 100
    return Math.min(Math.max(progress, 0), 100)
}

const getProfileColorStyle = (profile: UserProfile) => {
    if (
        profile.profile_color === "gradient" &&
        profile.gradient_colors &&
        profile.gradient_colors.length > 0
    ) {
        const gradientStops = profile.gradient_colors
            .map(color => `${color.color} ${color.position}%`)
            .join(", ")
        return `linear-gradient(135deg, ${gradientStops})`
    }
    return profile.linear_color || "#ffffff"
}

type ColorElement = "text_underline" | "bold_text" | "status" | "bio" | "social_icons"

type ColorType = "linear" | "gradient"

interface LinearColor {
    type: "linear"
    color: string
}

interface GradientColor {
    type: "gradient"
    name: string
    colors: Array<{
        color: string
        position: number
    }>
}

interface ProfileColors {
    profile: {
        type: ColorType
        linear_color: string
        gradient_colors: Array<{
            color: string
            position: number
        }>
    }
    elements: {
        [key in ColorElement]: LinearColor | GradientColor
    }
}

const getElementColor = (colors: ProfileColors, element: ColorElement) => {
    const elementColor = colors.elements[element]

    if (elementColor.type === "gradient") {
        const gradientStops = elementColor.colors
            .map(color => `${color.color} ${color.position}%`)
            .join(", ")
        return `linear-gradient(135deg, ${gradientStops})`
    }

    if (elementColor.type === "linear") {
        if (!elementColor.color) {
            switch (element) {
                case "text_underline":
                    return "#3391ff"
                case "bold_text":
                    return "#ffffff"
                case "status":
                    return "#ffffff"
                case "bio":
                    return "#ffffff"
                case "social_icons":
                    return "#ffffff"
                default:
                    return "#ffffff"
            }
        }
        return elementColor.color
    }

    return "#ffffff"
}

export default function ProfilePage({ params }: { params: { username: string } }) {
    const [profile, setProfile] = useState<UserProfile | null>(null)
    const [loading, setLoading] = useState(true)
    const [linkModal, setLinkModal] = useState<{ isOpen: boolean; url: string }>({
        isOpen: false,
        url: ""
    })
    const [showAllFriends, setShowAllFriends] = useState(false)
    const FRIENDS_TO_SHOW = 8
    const [guildData, setGuildData] = useState<DiscordGuild | null>(null)
    const [reportModal, setReportModal] = useState(false)
    const [reportReason, setReportReason] = useState("")
    const [selectedReason, setSelectedReason] = useState<(typeof reportReasons)[number] | "">("")
    const [error, setError] = useState<string | null>(null)
    const [shouldRefetch, setShouldRefetch] = useState(false)
    const [currentActivity, setCurrentActivity] = useState(0)
    const [isBlurred, setIsBlurred] = useState(true)
    const [volume, setVolume] = useState(0)
    const [isPlaying, setIsPlaying] = useState(true)
    const audioRef = useRef<HTMLAudioElement | null>(null)
    const { data: session } = useSession()
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [formattedBio, setFormattedBio] = useState("")
    const [isBioLoading, setIsBioLoading] = useState(true)

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const cleanUsername = decodeURIComponent(params.username as string).replace("@", "")
                const response = await fetch(`/api/socials`, {
                    method: "GET",
                    headers: {
                        "X-USER-ID": cleanUsername
                    }
                })

                if (!response.ok) {
                    throw new Error(`Failed to fetch profile (${response.status})`)
                }

                const data = await response.json()
                
                if (profile?.bio === data.bio) {
                    setProfile(prev => ({
                        ...data,
                        bio: prev?.bio || data.bio 
                    }))
                } else {
                    setProfile(data) 
                }
            } catch (error) {
                console.error("Failed to fetch profile:", error)
                setError(error instanceof Error ? error.message : "Failed to load profile")
            } finally {
                setLoading(false)
            }
        }

        fetchProfile()
        const interval = setInterval(fetchProfile, 30000)
        return () => clearInterval(interval)
    }, [params.username])

    useEffect(() => {
        if (profile?.discord_guild) {
            fetchGuildData(profile.discord_guild).then(data => {
                if (data?.guild) {
                    setGuildData({
                        id: data.guild.id,
                        name: data.guild.name,
                        icon: data.guild.icon,
                        member_count: data.approximate_member_count,
                        presence_count: data.approximate_presence_count,
                        description: data.guild.description
                    })
                }
            })
        }
    }, [profile?.discord_guild])

    useEffect(() => {
        if (audioRef.current && profile?.audio?.url && !isBlurred) {
            audioRef.current.volume = 0.5
            setVolume(0.5)
            audioRef.current.play()
        }
    }, [isBlurred, profile?.audio?.url])

    useEffect(() => {
        if (typeof window !== "undefined") {
            window.handleExternalLink = (element: HTMLAnchorElement) => {
                const url = element.getAttribute("data-url")
                if (url) {
                    setLinkModal({ isOpen: true, url })
                }
            }
        }
    }, [])

    useEffect(() => {
        async function formatBio() {
            if (profile?.bio) {
                setIsBioLoading(true)
                try {
                    const formatted = await formatDiscordText(profile.bio, profile.colors, params.username)
                    setFormattedBio(formatted)
                } catch (error) {
                    console.error("Failed to format bio:", error)
                } finally {
                    setIsBioLoading(false)
                }
            }
        }
        formatBio()
    }, [profile?.bio, profile?.colors, params.username])

    if (error) {
        return (
            <div
                className="min-h-screen flex items-center justify-center p-4"
                style={{
                    background: "rgb(0 0 0 / 0.95)"
                }}>
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="w-full max-w-[700px] rounded-xl overflow-hidden bg-black/40 backdrop-blur-sm border border-red-500/20 p-8">
                    <div className="flex flex-col items-center text-center gap-4">
                        <div className="p-3 rounded-full bg-red-500/10">
                            <AlertTriangle className="w-8 h-8 text-red-500" />
                        </div>
                        <h1 className="text-xl font-semibold text-white">Failed to Load Profile</h1>
                        <p className="text-red-400/80">{error}</p>
                        <button
                            onClick={() => window.location.reload()}
                            className="mt-2 px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-colors">
                            Try Again
                        </button>
                    </div>
                </motion.div>
            </div>
        )
    }

    if (loading) {
        return (
            <div
                className="min-h-screen flex items-center justify-center p-4"
                style={{
                    background: "rgb(0 0 0 / 0.95)"
                }}>
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="w-full max-w-[700px] rounded-xl overflow-hidden bg-black">
                    <div className="h-24 sm:h-32 md:h-48 bg-gradient-to-br from-zinc-900 to-black animate-pulse" />

                    <div className="p-4 sm:p-6">
                        <div className="relative -mt-12 sm:-mt-16 px-2 sm:px-6">
                            <div className="flex flex-col sm:flex-row sm:items-end gap-4">
                                <div className="relative mx-auto sm:mx-0">
                                    <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-full bg-zinc-900 animate-pulse" />
                                </div>

                                <div className="flex-1 text-center sm:text-left space-y-2">
                                    <div className="h-8 w-48 bg-zinc-900 rounded animate-pulse" />
                                    <div className="h-4 w-32 bg-zinc-900/50 rounded animate-pulse" />
                                </div>
                            </div>

                            <div className="mt-6 space-y-4">
                                <div className="h-32 bg-zinc-900/20 rounded-xl animate-pulse" />
                                <div className="h-24 bg-zinc-900/20 rounded-xl animate-pulse" />
                                <div className="h-24 bg-zinc-900/20 rounded-xl animate-pulse" />
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        )
    }

    if (!profile) return null

    const spotify = profile.presence?.activities?.find(activity => activity.name === "Spotify")
    const customStatus = profile.presence?.activities?.find(
        activity => activity.type === "ActivityType.custom" && activity.state
    )

    if (typeof window !== "undefined") {
        window.handleExternalLink = (element: HTMLAnchorElement) => {
            const url = element.getAttribute("data-url")
            if (url) {
                setLinkModal({ isOpen: true, url })
            }
        }
    }

    const getActivityIcon = (type: string) => {
        switch (type) {
            case "ActivityType.listening":
                return <Music className="w-4 h-4" />
            case "ActivityType.playing":
                return <Gamepad2 className="w-4 h-4" />
            default:
                return null
        }
    }

    const activity = profile.presence?.activities?.[currentActivity]

    const handleReport = async () => {
        // @ts-ignore
        if (!selectedReason || !reportReason || !session?.user?.email) {
            return
        }

        try {
            let response
            let retries = 0
            const maxRetries = 3

            while (retries < maxRetries) {
                response = await fetch("https://api.evict.bot/report", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${session?.user?.userToken}`
                    },
                    body: JSON.stringify({
                        username_reported: params.username,
                        reason: selectedReason,
                        description: reportReason,
                        // @ts-ignore
                        reporter_email: session?.user?.email
                    })
                })

                const data = await response.json()
                if (response.ok) break

                if (data.error === "You already have an active report for this user") {
                    setError("You already have an active report for this user")
                    setIsSubmitting(false)
                    return
                }

                retries++
                if (retries === maxRetries) {
                    setError("Failed to submit report after multiple attempts")
                    setIsSubmitting(false)
                    return
                }

                await new Promise(resolve => setTimeout(resolve, 1000))
            }

            setReportModal(false)
            setReportReason("")
            setSelectedReason("")
            setError(null)
            toast("Report submitted successfully", {
                style: {
                    background: "#111111",
                    border: "1px solid #222222",
                    color: "#fff"
                }
            })
        } catch (error) {
            setError("An unexpected error occurred. Please try again later.")
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div
            className="min-h-screen flex items-center justify-center p-4"
            style={{
                background: profile.background_url
                    ? `url(${profile.background_url}) center/cover no-repeat fixed`
                    : "rgb(0 0 0 / 0.95)"
            }}>
            <div className="w-full max-w-[700px]">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className={`w-full max-w-[700px] rounded-xl overflow-hidden ${
                        profile.glass_effect
                            ? "backdrop-blur-md bg-black/40 border border-white/5"
                            : "bg-black"
                    }`}>
                    <div className="relative">
                        <div
                            className={`h-24 sm:h-32 md:h-48 relative overflow-hidden 
                                ${!profile?.user?.banner ? "bg-gradient-to-br from-zinc-900 to-black" : ""}`}>
                            {profile?.user?.banner && (
                                <Image
                                    src={profile.user.banner}
                                    alt="Profile banner"
                                    fill
                                    className="object-cover"
                                    priority
                                />
                            )}
                        </div>

                        <div className="absolute top-4 right-4">
                            <button
                                onClick={() => {
                                    if (session) {
                                        setReportModal(true)
                                    } else {
                                        setLinkModal({
                                            isOpen: true,
                                            url:
                                                "/login?callbackUrl=" +
                                                encodeURIComponent(window.location.href)
                                        })
                                    }
                                }}
                                className="p-2 rounded-lg bg-black/20 backdrop-blur-sm hover:bg-black/30 transition-colors group">
                                <AlertTriangle className="w-5 h-5 text-red-500 group-hover:text-red-400" />
                            </button>
                        </div>

                        <div className={`${profile.glass_effect ? "bg-black/50" : "bg-black"} p-6`}>
                            <div className="relative -mt-16 sm:-mt-16 px-2 sm:px-6">
                                <div className="flex flex-col items-center sm:flex-row sm:items-end gap-4">
                                    <div className="relative">
                                        <div className="w-28 h-28 sm:w-32 sm:h-32 rounded-full overflow-hidden">
                                            <Image
                                                src={profile.user.avatar}
                                                alt={profile.user.name}
                                                width={128}
                                                height={128}
                                                unoptimized
                                                className="relative object-cover w-28 h-28 sm:w-32 sm:h-32"
                                                style={{ aspectRatio: "1/1", zIndex: 1 }}
                                            />
                                        </div>
                                        {profile.user.avatar_decoration_data?.asset && (
                                            <Image
                                                src={`https://cdn.discordapp.com/avatar-decoration-presets/${profile.user.avatar_decoration_data.asset}.png?size=256&passthrough=true`}
                                                alt=""
                                                width={128}
                                                height={128}
                                                unoptimized
                                                className="absolute -inset-0 w-full h-full scale-[1.2] pointer-events-none"
                                                style={{ zIndex: 2 }}
                                            />
                                        )}
                                        <div
                                            className={`absolute bottom-2 right-2 h-4 w-4 rounded-full ${statusColors[(profile.presence?.status as keyof typeof statusColors) || "offline"]} ${profile.colors.elements.status.type === "linear" && (profile.colors.elements.status as LinearColor).color ? "ring-2" : ""}`}
                                            style={{
                                                ...(profile.colors.elements.status.type ===
                                                    "linear" &&
                                                    (profile.colors.elements.status as LinearColor)
                                                        .color && {
                                                        borderColor: getElementColor(
                                                            profile.colors,
                                                            "status"
                                                        )
                                                    }),
                                                zIndex: 2
                                            }}
                                        />
                                    </div>

                                    <div className="flex-1 text-center sm:text-left">
                                        <div className="flex flex-col items-center sm:flex-row sm:items-center gap-1 sm:gap-2">
                                            <h1 className="text-2xl font-bold text-white">
                                                {profile.user.name}
                                            </h1>
                                            <div className="flex flex-wrap justify-center sm:justify-start gap-1">
                                                {profile.badges.map(badge => (
                                                    <div key={badge} className="group relative">
                                                        <Image
                                                            src={badgeIcons[badge as BadgeType]}
                                                            alt={badge}
                                                            width={24}
                                                            unoptimized
                                                            height={24}
                                                            className="w-5 h-5 sm:w-6 sm:h-6 object-contain"
                                                        />
                                                        <div
                                                            className="absolute -top-8 left-1/2 transform -translate-x-1/2 px-2 py-1 
                                                              bg-black rounded text-xs text-white opacity-0 group-hover:opacity-100 
                                                              transition-opacity duration-200 whitespace-nowrap pointer-events-none">
                                                            {badgeNames[badge as BadgeType]}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <p className="text-white/60 text-sm">
                                            Joined{" "}
                                            {format(new Date(profile.user.created_at), "MMMM yyyy")}
                                        </p>
                                    </div>
                                </div>

                                <div className="mt-6 p-4 bg-white/[0.02] rounded-xl border border-white/5">
                                    <div className="text-white/80 flex items-center gap-1">
                                        {isBioLoading ? (
                                            <div className="animate-pulse h-4 bg-white/10 rounded w-3/4 mb-2"></div>
                                        ) : (
                                            <div
                                                className="whitespace-pre-line text-white"
                                                style={{
                                                    ...(profile.colors.elements.bio.type ===
                                                    "gradient"
                                                        ? {
                                                              background: getElementColor(
                                                                  profile.colors,
                                                                  "bio"
                                                              ),
                                                              WebkitBackgroundClip: "text",
                                                              WebkitTextFillColor: "transparent",
                                                              backgroundClip: "text"
                                                          }
                                                        : {
                                                              color: getElementColor(
                                                                  profile.colors,
                                                                  "bio"
                                                              )
                                                          })
                                                }}
                                                dangerouslySetInnerHTML={{
                                                    __html: formattedBio
                                                }}
                                            />
                                        )}
                                        {profile?.bio_emoji?.url && (
                                            <Image
                                                src={profile.bio_emoji.url}
                                                alt={profile.bio_emoji.name || ""}
                                                width={20}
                                                height={20}
                                                unoptimized
                                                className="inline-block"
                                            />
                                        )}
                                    </div>
                                </div>

                                {customStatus && customStatus.state && (
                                    <div className="mt-4 p-4 bg-white/[0.02] rounded-xl border border-white/5">
                                        <div className="flex items-center gap-2 text-white/80">
                                            {customStatus.details_emoji &&
                                                renderEmoji(JSON.parse(customStatus.details_emoji))}
                                            {customStatus.state}
                                        </div>
                                    </div>
                                )}

                                {profile.presence?.activities?.length > 0 && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="mt-4 p-4 bg-white/[0.02] rounded-xl border border-white/5">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                {activity && activity.album_cover_url ? (
                                                    <Image
                                                        src={activity.album_cover_url}
                                                        alt="Album cover"
                                                        width={60}
                                                        height={60}
                                                        className="rounded-md"
                                                        unoptimized
                                                    />
                                                ) : (
                                                    activity &&
                                                    activity.large_image && (
                                                        <Image
                                                            src={activity.large_image}
                                                            alt={
                                                                activity.large_text ||
                                                                "Activity image"
                                                            }
                                                            unoptimized
                                                            width={60}
                                                            height={60}
                                                            className="rounded-md"
                                                        />
                                                    )
                                                )}
                                                <div>
                                                    <div className="flex items-center gap-2 text-white/60">
                                                        {getActivityIcon(activity.type)}
                                                        <span className="text-sm">
                                                            {activity.type ===
                                                            "ActivityType.listening"
                                                                ? "Listening to Spotify"
                                                                : activity.name}
                                                        </span>
                                                    </div>
                                                    <p className="text-white font-medium">
                                                        {activity.details}
                                                    </p>
                                                    <p className="text-white/60 text-sm">
                                                        {activity.state}
                                                    </p>

                                                    {profile.presence.activities.length > 1 && (
                                                        <div className="mt-2 flex items-center gap-2">
                                                            {profile.presence.activities.map(
                                                                (_, index) => (
                                                                    <button
                                                                        key={index}
                                                                        onClick={() =>
                                                                            setCurrentActivity(
                                                                                index
                                                                            )
                                                                        }
                                                                        className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${
                                                                            index ===
                                                                            currentActivity
                                                                                ? "bg-white/60 w-3"
                                                                                : "bg-white/20 hover:bg-white/30"
                                                                        }`}
                                                                    />
                                                                )
                                                            )}
                                                        </div>
                                                    )}

                                                    {activity.type === "ActivityType.listening" &&
                                                        activity.start &&
                                                        activity.end && (
                                                            <div className="mt-2">
                                                                <div className="h-1 bg-white/10 rounded-full w-[200px] overflow-hidden">
                                                                    <motion.div
                                                                        className="h-full"
                                                                        style={{
                                                                            background:
                                                                                profile.profile_color ===
                                                                                "gradient"
                                                                                    ? getProfileColorStyle(
                                                                                          profile
                                                                                      )
                                                                                    : profile.linear_color
                                                                        }}
                                                                        initial={{
                                                                            width: `${calculateProgress(activity.start, activity.end)}%`
                                                                        }}
                                                                        animate={{ width: "100%" }}
                                                                        transition={{
                                                                            duration:
                                                                                calculateRemaining(
                                                                                    activity.start,
                                                                                    activity.end
                                                                                ),
                                                                            repeat: 0,
                                                                            ease: "linear"
                                                                        }}
                                                                        onAnimationComplete={() => {
                                                                            setShouldRefetch(
                                                                                prev => !prev
                                                                            )
                                                                        }}
                                                                    />
                                                                </div>
                                                            </div>
                                                        )}
                                                </div>
                                            </div>

                                            {activity.type === "ActivityType.listening" && (
                                                <a
                                                    href={activity.track_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="p-3 rounded-full bg-green-500/10 hover:bg-green-500/20 transition-colors duration-200 group">
                                                    <svg
                                                        className="w-6 h-6 text-green-400 group-hover:text-green-300"
                                                        fill="currentColor"
                                                        viewBox="0 0 24 24">
                                                        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.018 17.184c-.225.36-.622.476-.953.257-2.609-1.591-5.909-1.954-9.784-1.069-.375.086-.743-.146-.829-.52-.086-.375.146-.743.52-.829 4.248-.969 7.912-.556 10.839 1.208.332.203.434.635.207.953zm1.34-2.979c-.283.45-.887.6-1.337.316-2.988-1.836-7.545-2.368-11.08-1.295-.456.138-.937-.122-1.075-.578-.138-.457.122-.938.578-1.075 4.037-1.225 9.065-.62 12.474 1.497.45.283.6.887.317 1.337zm.115-3.103c-3.584-2.128-9.497-2.324-12.914-1.286-.546.167-1.124-.142-1.29-.688-.167-.547.141-1.124.688-1.291 3.947-1.198 10.504-.969 14.653 1.485.533.317.711 1.006.394 1.54-.316.533-1.006.711-1.54.394z" />
                                                    </svg>
                                                </a>
                                            )}
                                        </div>
                                    </motion.div>
                                )}

                                <div className="mt-6">
                                    {profile.discord_guild && guildData && (
                                        <motion.div
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className="mb-6 p-3 sm:p-4 bg-white/[0.02] rounded-xl border border-white/5">
                                            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
                                                {guildData.icon && (
                                                    <Image
                                                        unoptimized
                                                        src={`https://cdn.discordapp.com/icons/${guildData.id}/${guildData.icon}.png?size=96`}
                                                        alt={guildData.name}
                                                        width={48}
                                                        height={48}
                                                        className="w-12 h-12 sm:w-[48px] sm:h-[48px] rounded-xl mx-auto sm:mx-0"
                                                    />
                                                )}
                                                <div className="flex-1 min-w-0 text-center sm:text-left">
                                                    <div className="flex items-center justify-center sm:justify-start gap-2 flex-wrap">
                                                        <h3 className="text-white font-medium truncate">
                                                            {guildData.name}
                                                        </h3>
                                                        <div className="px-2 py-0.5 bg-[#5865F2]/10 rounded text-xs text-[#5865F2]">
                                                            Discord Server
                                                        </div>
                                                    </div>
                                                    {guildData.description && (
                                                        <p className="text-white/60 text-sm mt-1 line-clamp-2">
                                                            {guildData.description}
                                                        </p>
                                                    )}
                                                    <div className="flex gap-4 mt-2 text-sm text-white/60 justify-center sm:justify-start flex-wrap">
                                                        <div className="flex items-center gap-1">
                                                            <div className="w-2 h-2 rounded-full bg-green-500" />
                                                            {guildData.presence_count.toLocaleString()}{" "}
                                                            online
                                                        </div>
                                                        <div className="flex items-center gap-1">
                                                            <div className="w-2 h-2 rounded-full bg-white/30" />
                                                            {guildData.member_count.toLocaleString()}{" "}
                                                            members
                                                        </div>
                                                    </div>
                                                </div>
                                                <a
                                                    href={`${profile.discord_guild}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="w-full sm:w-auto px-4 py-2 bg-[#5865F2] hover:bg-[#4752C4] transition-colors rounded-lg text-white text-sm font-medium text-center mt-3 sm:mt-0">
                                                    Join
                                                </a>
                                            </div>
                                        </motion.div>
                                    )}

                                    <h2 className="text-white/60 text-sm mb-3">Friends</h2>
                                    <div className="flex flex-wrap gap-3">
                                        {(showAllFriends
                                            ? profile.friends
                                            : profile.friends.slice(0, FRIENDS_TO_SHOW)
                                        ).map(friend => (
                                            <motion.div
                                                key={friend.id}
                                                initial={{ opacity: 0, scale: 0.9 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                className="relative group">
                                                <div className="w-12 h-12 rounded-full overflow-hidden">
                                                    <Image
                                                        src={friend.avatar}
                                                        alt={friend.name}
                                                        unoptimized
                                                        width={48}
                                                        height={48}
                                                        className="object-cover"
                                                    />
                                                </div>
                                                <div
                                                    className="absolute -top-8 left-1/2 transform -translate-x-1/2 px-2 py-1 
                                                  bg-black rounded text-xs text-white opacity-0 group-hover:opacity-100 
                                                  transition-opacity duration-200 whitespace-nowrap pointer-events-none">
                                                    @{friend.name}
                                                </div>
                                            </motion.div>
                                        ))}

                                        {profile.friends.length > FRIENDS_TO_SHOW && (
                                            <button
                                                onClick={() => setShowAllFriends(!showAllFriends)}
                                                className="w-12 h-12 rounded-full bg-white/5 hover:bg-white/10 
                                                     flex items-center justify-center text-white/60 text-sm 
                                                     transition-colors duration-200">
                                                {showAllFriends ? (
                                                    <span>−</span>
                                                ) : (
                                                    <span>
                                                        +{profile.friends.length - FRIENDS_TO_SHOW}
                                                    </span>
                                                )}
                                            </button>
                                        )}
                                    </div>
                                </div>

                                <div className="mt-6 flex gap-3">
                                    {profile.links.map(link => {
                                        const Icon =
                                            socialIcons[link.type as keyof typeof socialIcons] ||
                                            FaGlobe
                                        return (
                                            <a
                                                key={link.type}
                                                href={link.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{
                                                    color: getElementColor(
                                                        profile.colors,
                                                        "social_icons"
                                                    )
                                                }}
                                                className="p-2 bg-white/[0.02] rounded-lg hover:bg-white/[0.05] transition-colors duration-200">
                                                <Icon className="w-5 h-5" />
                                            </a>
                                        )
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>

            {profile.click.enabled && (
                <motion.div
                    className="fixed inset-0 flex items-center justify-center z-50"
                    initial={{ backdropFilter: "blur(10px)" }}
                    animate={{
                        backdropFilter: isBlurred ? "blur(10px)" : "blur(0px)",
                        opacity: isBlurred ? 1 : 0,
                        pointerEvents: isBlurred ? "auto" : "none"
                    }}
                    transition={{ duration: 0.5, ease: "easeInOut" }}
                    onClick={() => setIsBlurred(false)}
                    style={{ cursor: isBlurred ? "pointer" : "default" }}>
                    <motion.h1
                        className="text-2xl md:text-4xl font-bold text-white text-center font-mono"
                        animate={{
                            textShadow: [
                                "0 0 7px #fff",
                                "0 0 10px #fff",
                                "0 0 21px #fff",
                                "0 0 42px #0fa"
                            ]
                        }}
                        transition={{
                            duration: 2,
                            repeat: Infinity,
                            repeatType: "reverse"
                        }}>
                        {profile.click.text}
                    </motion.h1>
                </motion.div>
            )}

            <Dialog
                open={linkModal.isOpen}
                onOpenChange={() => setLinkModal({ isOpen: false, url: "" })}>
                <DialogContent className="bg-[#111111] border-[#222222] text-white p-6 rounded-xl max-w-md">
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-full bg-[#1a1a1a]">
                                <svg
                                    className="w-5 h-5 text-white/70"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24">
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                    />
                                </svg>
                            </div>
                            <h2 className="text-xl font-semibold">External Link</h2>
                        </div>

                        <p className="text-[#989898]">
                            You are leaving this site to visit an external website. Are you sure you
                            want to continue?
                            <br />
                            <br />
                            We are not responsible for any issues that may arise from visiting this
                            website.
                        </p>

                        <div className="bg-[#0a0a0a] p-3 rounded-lg border border-[#222222] break-all">
                            <span className="text-[#989898] font-medium">{linkModal.url}</span>
                        </div>

                        <div className="flex justify-end gap-3 pt-2">
                            <button
                                onClick={() => setLinkModal({ isOpen: false, url: "" })}
                                className="px-4 py-2 rounded-md text-[#989898] hover:text-white transition-colors">
                                Cancel
                            </button>
                            <button
                                onClick={() => {
                                    window.open(linkModal.url, "_blank", "noopener,noreferrer")
                                    setLinkModal({ isOpen: false, url: "" })
                                }}
                                className="px-4 py-2 rounded-md bg-[#5865F2] hover:bg-[#4752C4] transition-colors text-white font-medium">
                                Continue
                            </button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            <Dialog open={reportModal && !!session} onOpenChange={setReportModal}>
                <DialogContent className="bg-[#111111] border-[#222222] text-white p-6 rounded-xl max-w-md">
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-full bg-red-500/10">
                                <AlertTriangle className="w-5 h-5 text-red-500" />
                            </div>
                            <h2 className="text-xl font-semibold">Report Profile</h2>
                        </div>

                        {error && (
                            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                                {error}
                            </div>
                        )}

                        <p className="text-[#989898]">
                            Please select a reason and provide additional details for reporting this
                            profile.
                        </p>

                        <select
                            value={selectedReason}
                            onChange={e =>
                                setSelectedReason(e.target.value as (typeof reportReasons)[number])
                            }
                            className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#222222] rounded-lg text-white focus:outline-none focus:ring-1 focus:ring-[#333333]">
                            <option value="" disabled>
                                Select a reason
                            </option>
                            {reportReasons.map(reason => (
                                <option key={reason} value={reason}>
                                    {reason}
                                </option>
                            ))}
                        </select>

                        <textarea
                            value={reportReason}
                            onChange={e => setReportReason(e.target.value)}
                            placeholder="Provide additional details about your report..."
                            className="w-full h-32 px-3 py-2 bg-[#0a0a0a] border border-[#222222] rounded-lg text-white placeholder:text-[#666666] resize-none focus:outline-none focus:ring-1 focus:ring-[#333333]"
                        />

                        <div className="flex justify-end gap-3 pt-2">
                            <button
                                onClick={() => {
                                    setReportModal(false)
                                    setReportReason("")
                                    setSelectedReason("")
                                    setError(null)
                                }}
                                className="px-4 py-2 rounded-md text-[#989898] hover:text-white transition-colors">
                                Cancel
                            </button>
                            <button
                                onClick={async () => {
                                    setIsSubmitting(true)
                                    try {
                                        let response
                                        let retries = 0
                                        const maxRetries = 3

                                        while (retries < maxRetries) {
                                            response = await fetch("https://api.evict.bot/report", {
                                                method: "POST",
                                                headers: {
                                                    "Content-Type": "application/json",
                                                    Authorization: `Bearer ${session?.user?.userToken}`
                                                },
                                                body: JSON.stringify({
                                                    username_reported: params.username,
                                                    reason: selectedReason,
                                                    description: reportReason,
                                                    // @ts-ignore
                                                    reporter_email: session?.user?.email
                                                })
                                            })

                                            const data = await response.json()
                                            if (response.ok) break

                                            if (
                                                data.error ===
                                                "You already have an active report for this user"
                                            ) {
                                                setError(
                                                    "You already have an active report for this user"
                                                )
                                                setIsSubmitting(false)
                                                return
                                            }

                                            retries++
                                            if (retries === maxRetries) {
                                                setError(
                                                    "Failed to submit report after multiple attempts"
                                                )
                                                setIsSubmitting(false)
                                                return
                                            }

                                            await new Promise(resolve => setTimeout(resolve, 1000))
                                        }

                                        setReportModal(false)
                                        setReportReason("")
                                        setSelectedReason("")
                                        setError(null)
                                        toast("Report submitted successfully", {
                                            style: {
                                                background: "#111111",
                                                border: "1px solid #222222",
                                                color: "#fff"
                                            }
                                        })
                                    } catch (error) {
                                        setError(
                                            "An unexpected error occurred. Please try again later."
                                        )
                                    } finally {
                                        setIsSubmitting(false)
                                    }
                                }}
                                disabled={!selectedReason || !reportReason.trim() || isSubmitting}
                                className="px-4 py-2 rounded-md bg-red-500 hover:bg-red-600 transition-colors text-white disabled:opacity-50 disabled:cursor-not-allowed">
                                {isSubmitting ? "Submitting..." : "Submit Report"}
                            </button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {profile.audio?.url && (
                <>
                    <audio ref={audioRef} src={profile.audio.url} loop />
                    <div className="fixed top-4 left-4 z-[100]">
                        <div className="group relative">
                            <div className="absolute left-full ml-2 top-0 z-[101] pointer-events-auto">
                                <div className="p-3 rounded-xl bg-black/30 backdrop-blur-md border border-white/10 transform scale-0 group-hover:scale-100 transition-transform duration-200 origin-left min-w-[200px]">
                                    <div className="flex items-center justify-between mb-2">
                                        {profile.audio.title && (
                                            <p className="text-white/80 text-sm truncate">
                                                {profile.audio.title}
                                            </p>
                                        )}
                                        <button
                                            onClick={() => {
                                                if (audioRef.current) {
                                                    if (isPlaying) {
                                                        audioRef.current.pause()
                                                    } else {
                                                        audioRef.current.play()
                                                        audioRef.current.volume = volume
                                                    }
                                                    setIsPlaying(!isPlaying)
                                                }
                                            }}
                                            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors ml-2">
                                            {isPlaying ? (
                                                <Pause className="w-4 h-4 text-white/80" />
                                            ) : (
                                                <Play className="w-4 h-4 text-white/80" />
                                            )}
                                        </button>
                                    </div>
                                    <input
                                        type="range"
                                        min="0"
                                        max="1"
                                        step="0.01"
                                        value={volume}
                                        onChange={e => {
                                            const newVolume = parseFloat(e.target.value)
                                            setVolume(newVolume)
                                            if (audioRef.current) {
                                                audioRef.current.volume = newVolume
                                            }
                                        }}
                                        className="w-[160px] accent-white/80 bg-white/20 h-1 rounded-full appearance-none cursor-pointer"
                                    />
                                </div>
                            </div>

                            <button
                                onClick={() => {
                                    if (audioRef.current) {
                                        if (isPlaying) {
                                            audioRef.current.pause()
                                        } else {
                                            audioRef.current.play()
                                            audioRef.current.volume = volume
                                        }
                                        setIsPlaying(!isPlaying)
                                    }
                                }}
                                className="p-3 rounded-xl bg-black/30 backdrop-blur-md border border-white/10 hover:bg-black/40 transition-all duration-200">
                                {isPlaying ? (
                                    volume === 0 ? (
                                        <VolumeX className="w-5 h-5 text-white/80" />
                                    ) : volume < 0.5 ? (
                                        <Volume1 className="w-5 h-5 text-white/80" />
                                    ) : (
                                        <Volume2 className="w-5 h-5 text-white/80" />
                                    )
                                ) : (
                                    <VolumeX className="w-5 h-5 text-white/80" />
                                )}
                            </button>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}

declare global {
    interface Window {
        handleExternalLink: (element: HTMLAnchorElement) => void
    }
}
