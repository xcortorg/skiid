"use client"

import Loader from "@/components/(global)/Loader"
import { ChevronDown } from "lucide-react"
import Image from "next/image"
import { useCallback, useEffect, useRef, useState } from "react"
interface LevelData {
    guild_id: number
    guild_name: string
    level_roles: {
        role_id: number
        level: number
        role_name: string
        hex_color: string
    }[]
    users: {
        user_id: number
        xp: number
        level: number
        total_xp: number
        max_xp: number
        avatar_url: string
        username: string
        display_name: string
    }[]
}

interface Role {
    role_id: number
    level: number
    role_name: string
    hex_color: string
}

interface PageProps {
    params: {
        id: string
    }
}

export default function LeaderboardPage({ params }: PageProps) {
    const [data, setData] = useState<LevelData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [displayedUsers, setDisplayedUsers] = useState<LevelData["users"]>([])
    const [roles, setRoles] = useState<Role[]>([])
    const [page, setPage] = useState(1)
    const [hasMore, setHasMore] = useState(true)
    const observer = useRef<IntersectionObserver | null>(null)

    interface UserCardProps {
        display_name: string
        username: string
        level: number
        xp: number
        max_xp: number
        avatarSrc: string
        rank: number
    }

    function UserCard({
        display_name,
        username,
        level,
        xp,
        max_xp,
        avatarSrc,
        rank
    }: UserCardProps) {
        const progress = (xp / max_xp) * 100
        const isTopThree = rank <= 3

        return (
            <div
                className={`
                relative bg-evict-200 border border-evict-card-border rounded-xl p-6
                hover:border-white/20 transition-all duration-300
                ${isTopThree ? "shadow-lg shadow-black/50" : ""}
            `}>
                <div
                    className={`
                    absolute -left-3 top-1/2 -translate-y-1/2
                    w-8 h-8 rounded-full flex items-center justify-center
                    ${
                        rank === 1
                            ? "bg-amber-500"
                            : rank === 2
                              ? "bg-slate-400"
                              : rank === 3
                                ? "bg-amber-700"
                                : "bg-evict-400 border border-evict-card-border"
                    }
                `}>
                    <span className="text-white text-sm font-bold">{rank}</span>
                </div>

                <div className="flex items-center gap-4 ml-6">
                    <div className="relative w-12 h-12 rounded-full overflow-hidden border-2 border-evict-card-border">
                        <Image
                            src={avatarSrc}
                            alt={`${display_name}'s avatar`}
                            fill
                            className="object-cover"
                        />
                    </div>

                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <span className="text-white font-medium truncate">{display_name}</span>
                            <span className="text-white/40 text-sm">@{username}</span>
                        </div>

                        <div className="mt-2">
                            <div className="flex items-center justify-between mb-1.5">
                                <span className="text-white/60 text-sm font-medium">
                                    Level {level}
                                </span>
                                <span className="text-white/40 text-xs">
                                    {xp.toLocaleString()}/{max_xp.toLocaleString()} XP
                                </span>
                            </div>
                            <div className="h-1.5 bg-evict-400 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-300 ease-out
                                        ${
                                            rank === 1
                                                ? "bg-amber-500"
                                                : rank === 2
                                                  ? "bg-slate-400"
                                                  : rank === 3
                                                    ? "bg-amber-700"
                                                    : "bg-blue-500"
                                        }`}
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    function RoleList({ roles }: { roles: Role[] }) {
        const [isOpen, setIsOpen] = useState(true)
        const groupedRoles = roles.reduce(
            (acc, role) => {
                if (!acc[role.level]) acc[role.level] = []
                acc[role.level].push(role)
                return acc
            },
            {} as Record<number, Role[]>
        )

        return (
            <div className="bg-evict-200 border border-evict-card-border rounded-xl p-6 mb-8">
                <div
                    className="flex items-center gap-2 cursor-pointer mb-4"
                    onClick={() => setIsOpen(!isOpen)}>
                    <h2 className="text-xl font-bold text-white">Level Roles</h2>
                    <ChevronDown
                        className={`h-5 w-5 text-white/60 transition-transform duration-200 
                                  ${isOpen ? "rotate-180" : ""}`}
                    />
                </div>

                {isOpen && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(groupedRoles).map(([level, rolesForLevel]) => (
                            <div
                                key={level}
                                className="bg-evict-400 rounded-lg p-4 border border-evict-card-border">
                                <div className="text-white/40 text-sm">Level {level}</div>
                                <div className="flex flex-wrap gap-2 mt-2">
                                    {rolesForLevel.map(role => (
                                        <div
                                            key={role.role_id}
                                            className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs"
                                            style={{
                                                backgroundColor: `${role.hex_color}15`,
                                                color: role.hex_color
                                            }}>
                                            <span
                                                className="w-2 h-2 rounded-full"
                                                style={{ backgroundColor: role.hex_color }}
                                            />
                                            {role.role_name}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        )
    }

    const lastUserElementRef = useCallback(
        (node: HTMLElement | null) => {
            if (loading) return
            if (observer.current) observer.current.disconnect()
            observer.current = new IntersectionObserver(entries => {
                if (entries[0].isIntersecting && hasMore) {
                    setPage(prevPage => prevPage + 1)
                }
            })
            if (node) observer.current.observe(node)
        },
        [loading, hasMore]
    )

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch(`/api/levels`, {
                    headers: {
                        "X-GUILD-ID": params.id
                    }
                })

                if (response.status === 404) {
                    throw new Error("404 Not Found")
                }

                const result = await response.json()
                setData(result)
                if (result.level_roles && result.level_roles.length > 0) {
                    setRoles(result.level_roles)
                }
                setLoading(false)
            } catch (error) {
                console.log(error)
                setLoading(false)
                setError("This guild does not have any level data")
            }
        }

        fetchData()
    }, [params.id])

    useEffect(() => {
        if (data && data.users) {
            const sortedUsers = [...data.users].sort((a, b) => b.total_xp - a.total_xp)
            const start = (page - 1) * 50
            const end = page * 50
            const newUsers = sortedUsers.slice(start, end)
            setDisplayedUsers(prevUsers => [...prevUsers, ...newUsers])
            setHasMore(end < sortedUsers.length)
        }
    }, [data, page])

    if (loading) return <Loader />
    if (error) {
        return (
            <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
                <div className="text-white/60 text-center">
                    <p className="text-xl">{error}</p>
                    <a href="/" className="text-sm text-white/40 hover:text-white/60 mt-2 block">
                        Return Home
                    </a>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-[#0A0A0B]">
            <div className="relative border-b border-white/5 bg-black/20">
                <div className="absolute inset-0 top-0 bg-[url('/noise.png')] opacity-5" />
                <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-12 pt-24 relative">
                    <div className="text-center">
                        <h1 className="font-bold text-4xl sm:text-5xl text-white mt-8">
                            {data?.guild_name ?? "Unknown Guild"}
                        </h1>
                        <p className="text-white/60 mt-4 text-base sm:text-lg max-w-3xl mx-auto">
                            Server Leaderboard Rankings
                        </p>
                    </div>
                </div>
            </div>

            <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-8">
                {roles.length > 0 && <RoleList roles={roles} />}

                <div className="space-y-4">
                    {displayedUsers.map((user, index) => (
                        <div
                            key={user.user_id}
                            ref={index === displayedUsers.length - 1 ? lastUserElementRef : null}>
                            <UserCard
                                display_name={user.display_name}
                                username={user.username}
                                level={user.level}
                                xp={user.xp}
                                max_xp={user.max_xp}
                                avatarSrc={user.avatar_url}
                                rank={index + 1}
                            />
                        </div>
                    ))}
                </div>

                {loading && (
                    <div className="text-center py-8">
                        <Loader />
                    </div>
                )}
            </div>
        </div>
    )
}
