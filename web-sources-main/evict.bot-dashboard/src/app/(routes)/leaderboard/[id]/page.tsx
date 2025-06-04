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
            <div className={`
                relative bg-black/40 border border-white/5 rounded-lg p-4
                hover:bg-black/60 hover:border-white/10 transition-all duration-300
                ${isTopThree ? 'shadow-lg shadow-white/5' : ''}
                ${rank === 1 ? 'bg-gradient-to-r from-black/40 to-yellow-600/5' : 
                  rank === 2 ? 'bg-gradient-to-r from-black/40 to-slate-500/5' :
                  rank === 3 ? 'bg-gradient-to-r from-black/40 to-amber-900/5' : ''}
            `}>
                <div className={`
                    absolute -left-3 top-1/2 -translate-y-1/2
                    w-8 h-8 rounded-full flex items-center justify-center
                    ${rank === 1 ? 'bg-gradient-to-br from-yellow-400 to-yellow-600 shadow-lg shadow-yellow-600/20' :
                      rank === 2 ? 'bg-gradient-to-br from-slate-300 to-slate-500 shadow-lg shadow-slate-500/20' :
                      rank === 3 ? 'bg-gradient-to-br from-amber-700 to-amber-900 shadow-lg shadow-amber-900/20' :
                      'bg-black/60 border border-white/10'}
                `}>
                    <span className="text-white text-sm font-bold">{rank}</span>
                </div>

                <div className="flex items-center gap-4 ml-6">
                    <div className={`
                        relative w-12 h-12 rounded-full overflow-hidden 
                        border-2 ${isTopThree ? 'border-white/20' : 'border-white/10'}
                        ${isTopThree ? 'shadow-lg shadow-white/10' : ''}
                    `}>
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
                                <span className="text-white/60 text-sm font-medium">Level {level}</span>
                                <span className="text-white/40 text-xs">{xp.toLocaleString()}/{max_xp.toLocaleString()} XP</span>
                            </div>
                            <div className="h-1.5 bg-black/40 rounded-full overflow-hidden backdrop-blur-sm">
                                <div 
                                    className={`h-full rounded-full transition-all duration-300 ease-out
                                        ${rank === 1 ? 'bg-gradient-to-r from-yellow-400 to-yellow-600' :
                                          rank === 2 ? 'bg-gradient-to-r from-slate-300 to-slate-500' :
                                          rank === 3 ? 'bg-gradient-to-r from-amber-700 to-amber-900' :
                                          'bg-gradient-to-r from-blue-500 to-blue-400'}`}
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
        const groupedRoles = roles.reduce((acc, role) => {
            if (!acc[role.level]) acc[role.level] = []
            acc[role.level].push(role)
            return acc
        }, {} as Record<number, Role[]>)

        return (
            <div className="bg-black/40 border border-white/5 rounded-xl p-6 mb-8 backdrop-blur-sm">
                <div
                    className="flex items-center gap-2 cursor-pointer mb-4"
                    onClick={() => setIsOpen(!isOpen)}>
                    <h2 className="text-xl font-bold bg-gradient-to-r from-white via-white/90 to-white/80 text-transparent bg-clip-text">
                        Level Roles
                    </h2>
                    <ChevronDown
                        className={`h-5 w-5 text-white/60 transition-transform duration-200 
                                  ${isOpen ? "rotate-180" : ""}`}
                    />
                </div>
                
                {isOpen && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(groupedRoles).map(([level, rolesForLevel]) => (
                            <div key={level} className="space-y-2 bg-black/60 rounded-lg p-4 border border-white/5">
                                <div className="text-white/40 text-sm">Level {level}</div>
                                <div className="flex flex-wrap gap-2">
                                    {rolesForLevel.map(role => (
                                        <div
                                            key={role.role_id}
                                            className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs transition-all duration-300
                                                     hover:scale-105"
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
    if (error) return <div className="text-white/60 p-4">{error}</div>

    return (
        <div className="container mx-auto px-4 py-8 max-w-6xl">
            <div className="flex items-center justify-between mb-8">
                <h1 className="text-2xl md:text-3xl font-bold">
                    <span className="bg-gradient-to-r from-white via-white/90 to-white/80 text-transparent bg-clip-text">
                        {data?.guild_name ?? "Unknown Guild"}
                    </span>
                </h1>
            </div>

            {roles.length > 0 && <RoleList roles={roles} />}

            <div className="space-y-3">
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
                <div className="text-center py-4">
                    <Loader />
                </div>
            )}
        </div>
    )
}
