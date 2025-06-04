"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { fetchGuildStatistics } from "@/libs/dashboard/guild/statistics"
import { fetchGuildInvokes } from "@/libs/dashboard/guild/invokes"
import { checkBetaAccess } from "@/libs/dashboard/beta"
import { Beaker } from "lucide-react"
import { useState, useMemo, useEffect } from "react"
import { Line, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, LineChart, BarChart, Area, AreaChart } from "recharts"
import { format, parseISO } from "date-fns"
import { ArrowUp, ArrowDown, Activity, MessageSquare, Clock, Shield, Search, ChevronLeft, ChevronRight } from "lucide-react"
import Select from 'react-select'

const TIME_PERIODS = [
    { label: "7 Days", value: 7 },
    { label: "14 Days", value: 14 },
    { label: "30 Days", value: 30 }
]

const StatCardSkeleton = () => (
    <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
        <div className="animate-pulse">
            <div className="bg-white/5 w-8 h-8 rounded-lg mb-4" />
            <div className="space-y-2">
                <div className="bg-white/5 h-6 w-24 rounded" />
                <div className="bg-white/5 h-4 w-16 rounded" />
            </div>
        </div>
    </div>
)

const ChartSkeleton = () => (
    <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 md:p-6">
        <div className="animate-pulse">
            <div className="bg-white/5 h-6 w-32 rounded mb-6" />
            <div className="bg-white/5 h-[250px] md:h-[300px] w-full rounded" />
        </div>
    </div>
)

function BetaAccessRequired() {
    return (
        <div className="fixed inset-0 flex flex-col items-center justify-center text-center bg-[#0B0C0C] z-50">
            <div className="bg-blue-500/10 p-2 rounded-full mb-4">
                <Beaker className="w-8 h-8 text-blue-500" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Beta Access Required</h1>
            <p className="text-white/60 max-w-md">
                This feature is currently in beta. Join our Discord server to request access.
            </p>
        </div>
    )
}

export default function StatisticsPage({ params }: { params: { guildId: string } }) {
    const [selectedDays, setSelectedDays] = useState(7)
    const [searchQuery, setSearchQuery] = useState("")
    const [selectedCategory, setSelectedCategory] = useState<string>("")
    const [selectedUser, setSelectedUser] = useState<{ value: string; label: React.ReactNode } | null>(null)
    const [currentPage, setCurrentPage] = useState(1)
    const itemsPerPage = 25
    const queryClient = useQueryClient()

    useEffect(() => {
        const nextRanges = [14, 30]
        nextRanges.forEach(days => {
            queryClient.prefetchQuery({
                queryKey: ["statistics", params.guildId, days],
                queryFn: () => fetchGuildStatistics(params.guildId, days)
            })
        })
    }, [params.guildId, queryClient])

    const { data: betaAccess, isLoading: checkingBeta } = useQuery({
        queryKey: ["beta"],
        queryFn: checkBetaAccess
    })

    const { data: statsData, isLoading: statsLoading, isError: statsError, error: statsErrorData } = useQuery({
        queryKey: ["statistics", params.guildId, selectedDays],
        queryFn: () => fetchGuildStatistics(params.guildId, selectedDays),
        staleTime: 1000 * 60 * 5,
        placeholderData: (prev) => prev
    })

    const { data: invokesData, isLoading: invokesLoading } = useQuery({
        queryKey: ["invokes", params.guildId],
        queryFn: () => fetchGuildInvokes(params.guildId),
        staleTime: 1000 * 60 * 5
    })

    const userOptions = useMemo(() => {
        return invokesData?.users.map((user) => ({
            value: user.user_id,
            label: (
                <div className="flex items-center gap-2">
                    <img src={user.user_avatar} alt={user.user_name} className="w-6 h-6 rounded-full" />
                    <span>{user.user_displayname} <span className="text-zinc-400">@{user.user_name}</span></span>
                </div>
            )
        })) || []
    }, [invokesData?.users])

    const categoryOptions = useMemo(() => {
        const uniqueCategories = new Set(invokesData?.invokes.map(invoke => invoke.category) || [])
        return [
            { value: "", label: "All Categories" },
            ...Array.from(uniqueCategories).map(category => ({
                value: category,
                label: category
            }))
        ]
    }, [invokesData?.invokes])

    const filteredAndPaginatedData = useMemo(() => {
        const filtered = invokesData?.invokes.filter((invoke) => {
            const matchesSearch = invoke.command.toLowerCase().includes(searchQuery.toLowerCase())
            const matchesCategory = !selectedCategory || invoke.category === selectedCategory
            const matchesUser = !selectedUser || invoke.user_id === selectedUser.value
            return matchesSearch && matchesCategory && matchesUser
        }) || []

        const totalPages = Math.ceil(filtered.length / itemsPerPage)
        const startIndex = (currentPage - 1) * itemsPerPage
        const endIndex = startIndex + itemsPerPage

        return {
            data: filtered.slice(startIndex, endIndex),
            totalPages,
            totalItems: filtered.length
        }
    }, [invokesData?.invokes, searchQuery, selectedCategory, selectedUser, currentPage, itemsPerPage])

    if (checkingBeta) return null
    if (!betaAccess?.has_access) {
        return <BetaAccessRequired />
    }

    const content = (() => {
        if (statsLoading) {
            return (
                <div className="max-w-[1920px] mx-auto space-y-6 md:space-y-8">
                    <div className="animate-pulse space-y-2">
                        <div className="bg-white/5 h-8 w-32 rounded" />
                        <div className="bg-white/5 h-5 w-64 rounded" />
                    </div>

                    <div className="flex gap-2">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="bg-white/5 h-10 w-24 rounded-md animate-pulse" />
                        ))}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4">
                        {[...Array(4)].map((_, i) => (
                            <StatCardSkeleton key={i} />
                        ))}
                    </div>

                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 md:gap-6">
                        <ChartSkeleton />
                        <ChartSkeleton />
                    </div>
                </div>
            )
        }

        if (statsError) {
            return (
                <div className="flex items-center justify-center min-h-[200px]">
                    <div className="text-red-400">{(statsErrorData as Error).message}</div>
                </div>
            )
        }

        if (!statsData) return null
        
        const stats = statsData.statistics

        const calculateChange = (current: number, previous: number) => {
            if (previous === 0) return 100
            return ((current - previous) / previous) * 100
        }

        const getTotalForLastNDays = (days: number, metric: keyof Omit<typeof stats[0], 'date' | 'moderation'>) => {
            return stats.slice(0, days).reduce((sum, day) => sum + (day[metric] as number), 0)
        }

        const commandsChange = calculateChange(
            getTotalForLastNDays(7, "commands_used"),
            getTotalForLastNDays(7, "commands_used")
        )

        return (
            <div className="max-w-[1920px] mx-auto space-y-6 md:space-y-8">
                <div>
                    <h1 className="text-xl md:text-2xl font-bold text-white">Statistics</h1>
                    <p className="text-white/60">View your server&apos;s activity and trends</p>
                </div>

                <div className="flex gap-2 p-1 bg-white/5 rounded-lg w-fit overflow-x-auto">
                    {TIME_PERIODS.map((period) => (
                        <button
                            key={period.value}
                            onClick={() => setSelectedDays(period.value)}
                            className={`px-3 md:px-4 py-2 rounded-md transition-colors whitespace-nowrap ${
                                selectedDays === period.value
                                    ? "bg-white/10 text-white"
                                    : "text-white/60 hover:text-white"
                            }`}
                        >
                            {period.label}
                        </button>
                    ))}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4">
                    <StatCard
                        title="Commands Used"
                        value={getTotalForLastNDays(selectedDays, "commands_used")}
                        change={commandsChange}
                        icon={<Activity className="w-5 h-5" />}
                    />
                    <StatCard
                        title="Messages Sent"
                        value={getTotalForLastNDays(selectedDays, "messages_sent")}
                        change={calculateChange(
                            getTotalForLastNDays(7, "messages_sent"),
                            getTotalForLastNDays(7, "messages_sent")
                        )}
                        icon={<MessageSquare className="w-5 h-5" />}
                    />
                    <StatCard
                        title="Voice Minutes"
                        value={getTotalForLastNDays(selectedDays, "voice_minutes")}
                        change={calculateChange(
                            getTotalForLastNDays(7, "voice_minutes"),
                            getTotalForLastNDays(7, "voice_minutes")
                        )}
                        icon={<Clock className="w-5 h-5" />}
                    />
                    <StatCard
                        title="Mod Actions"
                        value={stats.slice(0, selectedDays).reduce((sum, day) => 
                            sum + Object.values(day.moderation).reduce((a, b) => a + b, 0), 0
                        )}
                        change={0}
                        icon={<Shield className="w-5 h-5" />}
                    />
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 md:gap-6">
                    <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 md:p-6">
                        <h3 className="text-base md:text-lg font-medium text-white mb-4 md:mb-6">Activity Trends</h3>
                        <div className="h-[250px] md:h-[300px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={[...stats].reverse()}>
                                    <XAxis 
                                        dataKey="date" 
                                        stroke="#666"
                                        tickFormatter={(date) => format(parseISO(date), "MMM d")}
                                    />
                                    <YAxis stroke="#666" />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "#1a1a1a",
                                            border: "1px solid rgba(255,255,255,0.1)",
                                            borderRadius: "8px"
                                        }}
                                        labelStyle={{ color: "#fff" }}
                                    />
                                    <Line 
                                        type="monotone" 
                                        dataKey="commands_used" 
                                        stroke="#8884d8" 
                                        strokeWidth={2}
                                        dot={false}
                                    />
                                    <Line 
                                        type="monotone" 
                                        dataKey="messages_sent" 
                                        stroke="#82ca9d"
                                        strokeWidth={2}
                                        dot={false}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 md:p-6">
                        <h3 className="text-base md:text-lg font-medium text-white mb-4 md:mb-6">Moderation Actions</h3>
                        <div className="h-[250px] md:h-[300px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={[...stats].reverse()}>
                                    <defs>
                                        <linearGradient id="moderationGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#8884d8" stopOpacity={0.3}/>
                                            <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
                                        </linearGradient>
                                    </defs>
                                    <XAxis 
                                        dataKey="date"
                                        stroke="#666"
                                        tickFormatter={(date) => format(parseISO(date), "MMM d")}
                                    />
                                    <YAxis stroke="#666" />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "#1a1a1a",
                                            border: "1px solid rgba(255,255,255,0.1)",
                                            borderRadius: "8px"
                                        }}
                                        labelStyle={{ color: "#fff" }}
                                    />
                                    <Area 
                                        type="monotone"
                                        dataKey={(data) => 
                                            data?.moderation 
                                                ? Object.values(data.moderation).reduce((a, b) => Number(a) + Number(b), 0)
                                                : 0
                                        }
                                        stroke="#8884d8"
                                        fill="url(#moderationGradient)"
                                        strokeWidth={2}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>

                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 md:p-6">
                    <h3 className="text-base md:text-lg font-medium text-white mb-4 md:mb-6">Moderation Breakdown</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3 md:gap-4">
                        {Object.entries(
                            stats.reduce((acc, day) => {
                                Object.entries(day.moderation).forEach(([action, count]) => {
                                    acc[action] = (acc[action] || 0) + count
                                })
                                return acc
                            }, {} as Record<string, number>)
                        ).map(([action, count]) => (
                            <div
                                key={action}
                                className="bg-white/5 rounded-lg p-4"
                            >
                                <div className="text-sm text-white/60">{action}</div>
                                <div className="text-2xl font-semibold text-white mt-1">{count}</div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="bg-[#111111] rounded-xl border border-[#222222] overflow-hidden">
                    <div className="p-4 border-b border-[#222222] flex flex-col sm:flex-row gap-4">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-500" />
                            <input 
                                type="text"
                                placeholder="Search commands..."
                                className="w-full bg-[#0B0C0C] text-sm rounded-xl pl-9 pr-4 h-[42.2px] border border-[#222222] focus:outline-none focus:border-[#333333] placeholder-zinc-500 text-white"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                        <div className="flex flex-col sm:flex-row gap-2">
                            <Select
                                className="w-full sm:w-[200px]"
                                classNames={{
                                    control: () => 
                                        'bg-[#0B0C0C] border border-[#222222] rounded-xl !min-h-0 h-[42px] !cursor-pointer hover:border-[#333333]',
                                    menu: () => 'bg-[#0B0C0C] border border-[#222222] rounded-xl mt-1',
                                    option: (state) => 
                                        `px-3 py-2 hover:bg-[#151515] ${state.isFocused ? 'bg-[#151515]' : ''} text-white`,
                                    placeholder: () => 'text-zinc-500',
                                    singleValue: () => 'text-white',
                                    input: () => 'text-white',
                                    menuList: () => 'py-2'
                                }}
                                styles={{
                                    control: (base) => ({
                                        ...base,
                                        boxShadow: 'none',
                                        backgroundColor: '#0B0C0C',
                                        borderColor: '#222222',
                                        '&:hover': {
                                            borderColor: '#333333'
                                        }
                                    }),
                                    menu: (base) => ({
                                        ...base,
                                        backgroundColor: '#0B0C0C',
                                        overflow: 'hidden'
                                    }),
                                    option: (base) => ({
                                        ...base,
                                        backgroundColor: 'transparent'
                                    })
                                }}
                                options={categoryOptions}
                                value={categoryOptions.find(opt => opt.value === selectedCategory)}
                                onChange={(option: any) => setSelectedCategory(option?.value || '')}
                                placeholder="All Categories"
                                components={{
                                    IndicatorSeparator: () => null
                                }}
                            />
                            <Select
                                className="w-full sm:w-[250px]"
                                classNames={{
                                    control: () => 
                                        'bg-[#0B0C0C] border border-[#222222] rounded-xl !min-h-0 h-[42px] !cursor-pointer hover:border-[#333333]',
                                    menu: () => 'bg-[#0B0C0C] border border-[#222222] rounded-xl mt-1',
                                    option: (state) => 
                                        `px-3 py-2 hover:bg-[#151515] ${state.isFocused ? 'bg-[#151515]' : ''} text-white`,
                                    placeholder: () => 'text-zinc-500',
                                    singleValue: () => 'text-white',
                                    input: () => 'text-white',
                                    menuList: () => 'py-2'
                                }}
                                styles={{
                                    control: (base) => ({
                                        ...base,
                                        boxShadow: 'none',
                                        backgroundColor: '#0B0C0C',
                                        borderColor: '#222222',
                                        '&:hover': {
                                            borderColor: '#333333'
                                        }
                                    }),
                                    menu: (base) => ({
                                        ...base,
                                        backgroundColor: '#0B0C0C',
                                        overflow: 'hidden'
                                    }),
                                    option: (base) => ({
                                        ...base,
                                        backgroundColor: 'transparent'
                                    })
                                }}
                                options={userOptions}
                                value={selectedUser}
                                onChange={(option: any) => setSelectedUser(option)}
                                placeholder="All Users"
                                components={{
                                    IndicatorSeparator: () => null
                                }}
                                isSearchable
                                isClearable
                            />
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-[#222222]">
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Command</th>
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Category</th>
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">User</th>
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Timestamp</th>
                                </tr>
                            </thead>
                            <tbody className="text-xs md:text-sm">
                                {filteredAndPaginatedData.data.map((invoke, index) => {
                                    const user = invokesData?.users.find(u => u.user_id === invoke.user_id)
                                    return (
                                        <tr key={index} className="border-t border-[#222222] hover:bg-[#151515]">
                                            <td className="py-3 px-4">{invoke.command}</td>
                                            <td className="py-3 px-4">
                                                <span className="px-2 py-1 rounded-md text-xs bg-[#222222]">
                                                    {invoke.category}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-2">
                                                    <img 
                                                        src={user?.user_avatar} 
                                                        alt={user?.user_name}
                                                        className="w-6 h-6 rounded-full"
                                                    />
                                                    <span>{user?.user_displayname} <span className="text-zinc-400">@{user?.user_name}</span></span>
                                                </div>
                                            </td>
                                            <td className="py-3 px-4 text-zinc-400">
                                                {new Date(invoke.timestamp).toLocaleString('en-GB')}
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>

                    <div className="flex flex-col sm:flex-row items-center justify-between border-t border-[#222222] px-4 py-3 gap-4">
                        <div>
                            <p className="text-xs md:text-sm text-zinc-400 text-center sm:text-left">
                                Showing <span className="font-medium text-white">{filteredAndPaginatedData.data.length > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0}</span> to{' '}
                                <span className="font-medium text-white">
                                    {Math.min(currentPage * itemsPerPage, filteredAndPaginatedData.totalItems)}
                                </span> of{' '}
                                <span className="font-medium text-white">{filteredAndPaginatedData.totalItems}</span> results
                            </p>
                        </div>
                        {filteredAndPaginatedData.totalPages > 1 && (
                            <div className="flex justify-center sm:justify-end w-full sm:w-auto">
                                <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                                    <button
                                        onClick={() => setCurrentPage(page => Math.max(1, page - 1))}
                                        disabled={currentPage === 1}
                                        className="relative inline-flex items-center rounded-l-md border border-[#222222] bg-[#0B0C0C] px-2 py-2 text-sm font-medium text-white hover:bg-[#151515] disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <span className="sr-only">Previous</span>
                                        <ChevronLeft className="h-5 w-5" aria-hidden="true" />
                                    </button>
                                    <button
                                        onClick={() => setCurrentPage(page => Math.min(filteredAndPaginatedData.totalPages, page + 1))}
                                        disabled={currentPage === filteredAndPaginatedData.totalPages}
                                        className="relative inline-flex items-center rounded-r-md border border-[#222222] bg-[#0B0C0C] px-2 py-2 text-sm font-medium text-white hover:bg-[#151515] disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <span className="sr-only">Next</span>
                                        <ChevronRight className="h-5 w-5" aria-hidden="true" />
                                    </button>
                                </nav>
                            </div>
                        )}
                    </div>

                    {(invokesLoading || !invokesData || filteredAndPaginatedData.data.length === 0) && (
                        <div className="text-center py-8 text-zinc-400">
                            {invokesLoading ? "Loading command history..." : "No command history available."}
                        </div>
                    )}
                </div>
            </div>
        )
    })()

    return content
}

interface StatCardProps {
    title: string
    value: number
    change: number
    icon: React.ReactNode
}

function StatCard({ title, value, change, icon }: StatCardProps) {
    return (
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
            <div className="flex items-center justify-between">
                <div className="bg-white/5 p-2 rounded-lg">
                    {icon}
                </div>
                {change !== 0 && (
                    <div className={`flex items-center gap-1 text-sm ${
                        change > 0 ? "text-green-400" : "text-red-400"
                    }`}>
                        {change > 0 ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                        {Math.abs(change).toFixed(1)}%
                    </div>
                )}
            </div>
            <div className="mt-4">
                <div className="text-2xl font-semibold text-white">{value.toLocaleString()}</div>
                <div className="text-sm text-white/60">{title}</div>
            </div>
        </div>
    )
} 