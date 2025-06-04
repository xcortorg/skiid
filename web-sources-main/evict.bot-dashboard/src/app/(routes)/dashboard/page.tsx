"use client"

console.log('Dashboard module loading')

import { useEffect } from "react"
import { motion } from "framer-motion"
import Image from "next/image"
import { HiOutlineCog, HiServer } from "react-icons/hi"
import { fetchUserGuilds } from "@/libs/dashboard/guild"
import type { DiscordGuild } from "@/libs/dashboard/guild"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { checkBetaAccess } from "@/libs/dashboard/beta"
import { checkDashboardAuth } from "@/libs/dashboard/auth"

export default function DashboardPage() {
    console.log('Dashboard component rendering')
    const router = useRouter()

    useEffect(() => {
        console.log('Auth effect running')
        const hasAuth = checkDashboardAuth()
        console.log('Has auth:', hasAuth)
        
        if (!hasAuth) {
            console.log('No auth, redirecting')
            router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`)
        }
    }, [router])

    const { data: betaAccess } = useQuery({
        queryKey: ["beta"],
        queryFn: checkBetaAccess,
        staleTime: 1000 * 60 * 5,
        retry: false
    })

    const { data, isLoading, error } = useQuery({
        queryKey: ["guilds"],
        queryFn: fetchUserGuilds,
        staleTime: 1000 * 60 * 5,
        retry: 1
    })

    useEffect(() => {
        if (error) console.log('Query error:', error)
        if (error instanceof Error && error.message === "Unauthorized") {
            console.log('Unauthorized error, redirecting to login')
            const currentPath = window.location.pathname
            router.push(`/login?redirect=${encodeURIComponent(currentPath)}`)
        }
    }, [error, router])

    useEffect(() => {
        if (betaAccess && !betaAccess.has_access) {
            const currentPath = window.location.pathname
            router.push(`/login?redirect=${encodeURIComponent(currentPath)}`)
        }
    }, [betaAccess, router])

    if (isLoading) {
        return <LoadingSkeleton />
    }

    if (error) {
        return (
            <div className="min-h-screen bg-black/95 flex items-center justify-center">
                <div className="text-red-400">
                    {error instanceof Error ? error.message : "Failed to load dashboard"}
                </div>
            </div>
        )
    }

    const sortGuilds = (guilds: DiscordGuild[]) => {
        return guilds.sort((a, b) => {
            const aCanManage = a.permissions.manage_guild || a.permissions.admin
            const bCanManage = b.permissions.manage_guild || b.permissions.admin
            if (aCanManage && !bCanManage) return -1
            if (!aCanManage && bCanManage) return 1

            if (a.mutual && !b.mutual) return -1
            if (!a.mutual && b.mutual) return 1
            
            return a.name.localeCompare(b.name)
        })
    }

    return (
        <div className="min-h-screen bg-black/95 p-8">
            <div className="max-w-7xl mx-auto">
                <div className="mb-12">
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center gap-4"
                    >
                        <div className="w-16 h-16 rounded-full overflow-hidden">
                            <Image
                                src={data?.user.avatar ? `https://cdn.discordapp.com/avatars/${data.user.id}/${data.user.avatar}.png` : "/default-avatar.png"}
                                alt="User avatar"
                                width={64}
                                height={64}
                                className="object-cover"
                            />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold text-white">Welcome, {data?.user.username}</h1>
                            <p className="text-white/60">Manage your Discord servers</p>
                        </div>
                    </motion.div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {data?.guilds && sortGuilds(data.guilds).map((guild) => (
                        <motion.div
                            key={guild.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                      hover:border-white/10 transition-all duration-300 overflow-hidden flex flex-col`}
                        >
                            <div className="relative z-10">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="w-12 h-12 rounded-full overflow-hidden bg-white/[0.02]">
                                        {guild.icon ? (
                                            <Image
                                                src={`https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png`}
                                                alt={guild.name}
                                                width={48}
                                                height={48}
                                                className="object-cover"
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center">
                                                <HiServer className="w-6 h-6 text-white/60" />
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-semibold text-white">{guild.name}</h3>
                                        <p className="text-sm text-white/60">
                                            {guild.owner ? "Owner" : 
                                             guild.permissions.admin ? "Admin" : 
                                             guild.permissions.manage_guild ? "Manager" : 
                                             "Member"}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-2 mt-auto relative z-20">
                                {guild.mutual ? (
                                    guild.permissions.manage_guild || guild.permissions.admin ? (
                                        <a
                                            href={`/dashboard/${guild.id}`}
                                            className="flex-1 bg-white/5 hover:bg-white/10 text-white h-10 px-4 rounded-lg 
                                                     transition-colors duration-200 flex items-center justify-center"
                                        >
                                            <span>Manage</span>
                                        </a>
                                    ) : (
                                        <div className="flex-1 bg-white/5 text-white/40 h-10 px-4 rounded-lg 
                                                  cursor-not-allowed flex items-center justify-center">
                                            No Permission
                                        </div>
                                    )
                                ) : (
                                    guild.permissions.manage_guild || guild.permissions.admin ? (
                                        <a 
                                            href={`https://discord.com/api/oauth2/authorize?client_id=1203514684326805524&permissions=8&scope=bot&guild_id=${guild.id}`}
                                            className="flex-1 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-200 h-10 px-4 rounded-lg 
                                             transition-colors duration-200 flex items-center justify-center gap-2 cursor-pointer"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            <HiServer className="w-5 h-5" />
                                            Add to Server
                                        </a>
                                    ) : (
                                        <div className="flex-1 bg-white/5 text-white/40 h-10 px-4 rounded-lg 
                                                  cursor-not-allowed flex items-center justify-center">
                                            No Permission
                                        </div>
                                    )
                                )}
                                {(guild.mutual && (guild.permissions.manage_guild || guild.permissions.admin)) && (
                                    <button className="bg-white/5 hover:bg-white/10 text-white h-10 w-10 rounded-lg 
                                             transition-colors duration-200 flex items-center justify-center cursor-pointer">
                                        <HiOutlineCog className="w-5 h-5" />
                                    </button>
                                )}
                            </div>

                            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent 
                                          opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            {!guild.mutual && (
                                <div className="absolute top-2 right-2 px-2 py-1 bg-indigo-500/20 rounded-md">
                                    <span className="text-xs text-indigo-200">Not Added</span>
                                </div>
                            )}
                        </motion.div>
                    ))}
                </div>
            </div>
        </div>
    )
}

function LoadingSkeleton() {
    return (
        <div className="min-h-screen bg-black/95 p-8">
            <div className="max-w-7xl mx-auto">
                <div className="mb-12">
                    <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-full bg-white/10 animate-pulse" />
                        <div>
                            <div className="h-8 w-48 bg-white/10 rounded animate-pulse mb-2" />
                            <div className="h-4 w-32 bg-white/10 rounded animate-pulse" />
                        </div>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1,2,3].map((i) => (
                        <div key={i} className="bg-white/[0.02] border border-white/5 rounded-xl p-6 animate-pulse">
                            <div className="h-32 bg-white/10 rounded" />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}