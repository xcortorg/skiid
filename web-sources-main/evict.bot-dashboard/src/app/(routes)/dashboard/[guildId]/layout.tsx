"use client"

import { checkBetaAccess } from "@/libs/dashboard/beta"
import { DashboardResponse, DiscordGuild, fetchUserGuilds } from "@/libs/dashboard/guild"
import { navigation } from "@/libs/dashboard/navigation"
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query"
import { AlertTriangle, Bell, ChevronDown, Check, Info, Menu, X } from "lucide-react"
import Image from "next/image"
import Link from "next/link"
import { usePathname, useRouter, useSelectedLayoutSegment } from "next/navigation"
import React, { useEffect, useState } from "react"
import toast, { Toaster } from "react-hot-toast"
import UserAvatar from "@/components/UserAvatar"
import { format } from "date-fns"

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000 * 60 * 5,
            gcTime: 1000 * 60 * 30,
            refetchOnWindowFocus: false,
            retry: 1
        }
    }
})

interface ChildProps {
    guild?: DiscordGuild
    userGuilds?: DiscordGuild[]
}

export default function DashboardLayout({
    children,
    params
}: {
    children: React.ReactNode
    params: { guildId: string }
}) {
    const segment = useSelectedLayoutSegment()
    const [userImage, setUserImage] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const image = localStorage.getItem('userImage')
        setUserImage(image)
        setLoading(false)
    }, [])

    if (segment === 'music') {
        return (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        )
    }

    return (
        <QueryClientProvider client={queryClient}>
            <DashboardLayoutContent params={params}>{children}</DashboardLayoutContent>
            <Toaster
                position="bottom-right"
                toastOptions={{
                    style: {
                        background: "#333",
                        color: "#fff"
                    }
                }}
            />
        </QueryClientProvider>
    )
}

function ComingSoon() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            <h1 className="text-3xl font-bold text-white mb-4">Coming Soon</h1>
            <p className="text-white/60 max-w-md">
                We&apos;re working hard to bring you this feature. Stay tuned for updates!
            </p>
        </div>
    )
}

function DashboardLayoutContent({
    children,
    params
}: {
    children: React.ReactNode
    params: { guildId: string }
}) {
    const router = useRouter()
    const pathname = usePathname()
    const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false)
    const [isGuildSelectorOpen, setIsGuildSelectorOpen] = useState(false)
    const [userImage, setUserImage] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [isOpen, setIsOpen] = useState(false)

    const { data: betaAccess, isLoading: isBetaLoading } = useQuery({
        queryKey: ["beta"],
        queryFn: checkBetaAccess,
        staleTime: 1000 * 60 * 15,
        retry: false
    })

    const { data: userGuilds, isLoading: isGuildsLoading } = useQuery({
        queryKey: ["guilds"],
        queryFn: fetchUserGuilds,
        staleTime: 1000 * 60 * 5,
        placeholderData: (prev) => prev
    })

    useEffect(() => {
        if (
            userGuilds &&
            !userGuilds.guilds?.some(g => g.id === params.guildId)
        ) {
            router.push("/dashboard")
            return
        }

        if (betaAccess && !betaAccess.has_access) {
            const currentPath = window.location.pathname
            router.push(`/login?redirect=${encodeURIComponent(currentPath)}&forBeta=true`)
        }
    }, [betaAccess, router, userGuilds, params.guildId])

    useEffect(() => {
        const image = localStorage.getItem('userImage')
        setUserImage(image)
        setLoading(false)
    }, [])

    const currentGuild = userGuilds?.guilds?.find(g => g.id === params.guildId) || {
        id: params.guildId,
        name: "Loading...",
        icon: null,
        owner: false,
        permissions: {
            admin: false,
            manage_guild: false,
            manage_roles: false,
            manage_channels: false,
            kick_members: false,
            ban_members: false,
            value: 0
        },
        features: [],
        mutual: false
    } as DiscordGuild
    const currentPage = Object.values(navigation)
        .flat()
        .find(item => pathname === `/dashboard/${currentGuild?.id}${item.href}`)

    const isComingSoonPage = currentPage?.isComingSoon

    const filteredGuilds =
        (userGuilds as DashboardResponse)?.guilds?.filter(
            g => g.permissions.manage_guild || g.permissions.admin || g.owner
        ) || []

    useEffect(() => {
        setIsSidebarOpen(false)
    }, [pathname])

    if (isBetaLoading || isGuildsLoading) {
        return (
            <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
                <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-white border-r-2 border-b-2 border-transparent mb-4"></div>
                    <h2 className="text-xl font-semibold text-white">Loading your dashboard...</h2>
                    <p className="text-white/60 mt-2">Please wait while we fetch your data</p>
                </div>
            </div>
        )
    }

    if (userGuilds) {
        return (
            <div className="min-h-screen bg-[#0B0C0C]">
                <div className="bg-[#0B0C0C] w-full h-[70px] border-b border-white/5 shrink-0">
                    <div className="h-full px-6 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                                className="lg:hidden text-white/60 hover:text-white transition-colors">
                                {isSidebarOpen ? (
                                    <X className="w-5 h-5" />
                                ) : (
                                    <Menu className="w-5 h-5" />
                                )}
                            </button>

                            <Link href="/" className="flex items-center gap-3">
                                <Image
                                    src="https://r2.evict.bot/evict-new.png"
                                    alt="evict"
                                    width={32}
                                    height={32}
                                    className="rounded-lg"
                                />
                                <span className="text-xl font-semibold text-white">evict</span>
                            </Link>
                        </div>

                        <div className="flex items-center gap-6">
                            <div className="relative">
                                <button 
                                    onClick={() => setIsOpen(!isOpen)} 
                                    className="text-white/60 hover:text-white transition-colors"
                                >
                                    <Bell className="w-5 h-5" />
                                    {userGuilds?.notifications?.length > 0 && (
                                        <span className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full" />
                                    )}
                                </button>

                                {isOpen && (
                                    <>
                                        <div 
                                            className="fixed inset-0 z-40" 
                                            onClick={() => setIsOpen(false)} 
                                        />
                                        <div className="absolute right-0 mt-2 w-80 bg-[#111111] border border-white/5 rounded-xl shadow-lg z-50">
                                            <div className="p-4">
                                                <h3 className="text-sm font-medium text-white">Notifications</h3>
                                                <div className="mt-2 space-y-2">
                                                    {userGuilds?.notifications?.length === 0 ? (
                                                        <p className="text-sm text-white/60">No notifications</p>
                                                    ) : (
                                                        userGuilds?.notifications?.map(notification => (
                                                            <div key={notification.id} className="p-3 bg-white/[0.02] rounded-lg">
                                                                <div className="flex items-start gap-2">
                                                                    {notification.type === "info" && <Info className="w-4 h-4 text-blue-400 mt-0.5" />}
                                                                    {notification.type === "warning" && <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5" />}
                                                                    {notification.type === "error" && <X className="w-4 h-4 text-red-400 mt-0.5" />}
                                                                    {notification.type === "success" && <Check className="w-4 h-4 text-green-400 mt-0.5" />}
                                                                    <div>
                                                                        <p className="text-sm font-medium text-white">{notification.title}</p>
                                                                        <p className="text-sm text-white/60">{notification.content}</p>
                                                                        <p className="text-xs text-white/40 mt-1">
                                                                            {format(new Date(notification.created_at), "MMM d, yyyy")}
                                                                        </p>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        ))
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </>
                                )}
                            </div>
                            <UserAvatar />
                        </div>
                    </div>
                </div>

                <div className="flex">
                    {isSidebarOpen && (
                        <div
                            className="fixed inset-0 bg-black/50 lg:hidden z-40"
                            onClick={() => setIsSidebarOpen(false)}
                        />
                    )}

                    <aside
                        className={`
                        fixed lg:static inset-y-0 left-0 w-64 bg-[#0A0A0B] border-r border-white/5 transition-transform duration-200 ease-in-out z-50 lg:translate-x-0
                        ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}
                    `}>
                        <div className="p-4">
                            <div
                                className="relative"
                                onMouseLeave={() => setIsGuildSelectorOpen(false)}>
                                <button
                                    onClick={() => setIsGuildSelectorOpen(!isGuildSelectorOpen)}
                                    className="w-full flex items-center gap-3 p-3 bg-white/[0.02] rounded-lg border border-white/5 hover:bg-white/[0.04] transition-colors">
                                    <Image
                                        src={
                                            currentGuild?.icon
                                                ? `https://cdn.discordapp.com/icons/${currentGuild.id}/${currentGuild.icon}.png`
                                                : "https://cdn.discordapp.com/embed/avatars/1.png"
                                        }
                                        alt={currentGuild?.name ?? ""}
                                        width={40}
                                        height={40}
                                        className="rounded-lg"
                                    />
                                    <div className="flex-1 truncate">
                                        <h3 className="text-white font-medium truncate">
                                            {currentGuild?.name}
                                        </h3>
                                        <p className="text-sm text-white/40">Server Settings</p>
                                    </div>
                                    <ChevronDown
                                        className={`w-5 h-5 text-white/40 transition-transform ${isGuildSelectorOpen ? "rotate-180" : ""}`}
                                    />
                                </button>

                                {isGuildSelectorOpen && (
                                    <>
                                        <div className="absolute left-0 right-0 h-2 -bottom-2" />
                                        <div
                                            onMouseEnter={() => setIsGuildSelectorOpen(true)}
                                            className="absolute top-full left-0 right-0 mt-2 py-2 bg-[#0B0C0C] border border-white/5 rounded-lg shadow-xl z-50 max-h-[300px] overflow-y-auto">
                                            {filteredGuilds.map(guild => (
                                                <Link
                                                    key={guild.id}
                                                    href={`/dashboard/${guild.id}`}
                                                    className={`flex items-center gap-3 px-3 py-2 hover:bg-white/5 transition-colors
                                                        ${guild.id === currentGuild?.id ? "bg-white/10" : ""}`}>
                                                    <Image
                                                        src={
                                                            guild.icon
                                                                ? `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png`
                                                                : "https://cdn.discordapp.com/embed/avatars/1.png"
                                                        }
                                                        alt={guild.name}
                                                        width={32}
                                                        height={32}
                                                        className="rounded-lg"
                                                    />
                                                    <div className="flex-1 truncate">
                                                        <h4 className="text-sm text-white truncate">
                                                            {guild.name}
                                                        </h4>
                                                    </div>
                                                </Link>
                                            ))}
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>

                        <nav className="mt-4 px-3">
                            {Object.entries(navigation).map(([category, items]) => (
                                <div key={category} className="mb-6">
                                    <h4 className="px-3 mb-2 text-xs font-medium text-white/40 uppercase tracking-wider">
                                        {category}
                                    </h4>
                                    <div className="space-y-1">
                                        {items.map(item => (
                                            <Link
                                                key={item.name}
                                                href={
                                                    item.isComingSoon
                                                        ? "#"
                                                        : `/dashboard/${currentGuild?.id}${item.href}`
                                                }
                                                onClick={e => {
                                                    if (item.isComingSoon) {
                                                        e.preventDefault()
                                                        toast.error("This feature is coming soon!")
                                                    }
                                                }}
                                                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
                                                    ${
                                                        pathname ===
                                                        `/dashboard/${currentGuild?.id}${item.href}`
                                                            ? "bg-white/10 text-white"
                                                            : "text-white/60 hover:text-white hover:bg-white/5"
                                                    }
                                                    ${item.isComingSoon ? "opacity-50" : ""}`}>
                                                <item.icon className="w-4 h-4" />
                                                <span>{item.name}</span>
                                                {item.isComingSoon && (
                                                    <span className="ml-auto text-xs bg-white/10 px-2 py-0.5 rounded">
                                                        Soon
                                                    </span>
                                                )}
                                            </Link>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </nav>
                    </aside>

                    <main className="flex-1 min-h-[calc(100vh-70px)]">
                        <div className="p-4 md:p-6">
                            {isComingSoonPage ? (
                                <ComingSoon />
                            ) : (
                                React.Children.map(children, child => {
                                    if (React.isValidElement(child)) {
                                        return React.cloneElement(
                                            child as React.ReactElement<ChildProps>,
                                            {
                                                guild: currentGuild,
                                                userGuilds: (userGuilds as DashboardResponse)
                                                    ?.guilds
                                            }
                                        )
                                    }
                                    return child
                                })
                            )}
                        </div>
                    </main>
                </div>
            </div>
        )
    }

    return null
}
