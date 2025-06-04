"use client"

import { fetchGuildLogging, LogEntry, MessageEditContent, RoleUpdateContent, ChannelUpdateContent } from "@/libs/dashboard/guild/logging"
import { useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import { ChevronLeft, ChevronRight, Eye, Search, Beaker } from "lucide-react"
import { useState, useEffect } from "react"
import Select from "react-select"
import LogDetailsModal from "../components/logs/LogDetailsModal"
import { checkBetaAccess } from "@/libs/dashboard/beta"
import { useRouter } from "next/navigation"

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

export default function LogsPage({ params }: { params: { guildId: string } }) {
    const [currentPage, setCurrentPage] = useState(1)
    const [searchQuery, setSearchQuery] = useState("")
    const [selectedChannel, setSelectedChannel] = useState<any>(null)
    const [selectedEvent, setSelectedEvent] = useState<any>(null)
    const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null)
    const router = useRouter()
    const itemsPerPage = 30

    const { data: betaAccess } = useQuery({
        queryKey: ["beta"],
        queryFn: checkBetaAccess,
        staleTime: 1000 * 60 * 15
    })

    const { data: loggingData, isLoading } = useQuery({
        queryKey: ["logging", params.guildId],
        queryFn: () => fetchGuildLogging(params.guildId),
        enabled: !!betaAccess?.has_access,
        staleTime: 1000 * 60 * 5,
        placeholderData: (prev) => prev
    })

    useEffect(() => {
        if (betaAccess && !betaAccess.has_access) {
            const currentPath = window.location.pathname
            router.push(`/login?redirect=${encodeURIComponent(currentPath)}&forBeta=true`)
        }
    }, [betaAccess, router])

    if (!betaAccess?.has_access) {
        return <BetaAccessRequired />
    }

    const users: Record<string, { name: string | null; bot: boolean | null }> = {};
    const channels: Record<string, { name: string; type: string }> = {};

    if (loggingData?.logs) {
        loggingData.logs.forEach(log => {
            if ('author' in log.content && log.content.author) {
                users[log.content.author.id] = {
                    name: log.content.author.name || log.content.author.display_name,
                    bot: log.content.author.bot
                }
            }
            if ('user' in log.content && log.content.user) {
                users[log.content.user.id] = {
                    name: log.content.user.name,
                    bot: log.content.user.bot
                }
            }
            if ('member' in log.content && log.content.member) {
                users[log.content.member.id] = {
                    name: log.content.member.display_name || log.content.member.name,
                    bot: 'bot' in log.content.member ? log.content.member.bot : false
                }
            }

            if ('channel' in log.content && log.content.channel) {
                channels[log.content.channel.id] = {
                    name: log.content.channel.name,
                    type: log.content.channel.type
                }
            }
            if ('target' in log.content && log.content.target?.channel_id) {
                channels[log.content.target.channel_id] = {
                    name: log.content.target.channel_name || 'unknown',
                    type: log.content.target.channel_type || 'unknown'
                }
            }
        });
    }

    const channelOptions = loggingData?.channels.map(channel => ({
        value: channel.channel_id,
        label: `#${channel.channel_name}`
    })) || []

    const eventOptions = loggingData?.available_events 
        ? Object.entries(loggingData.available_events).map(([key]) => ({
            value: key,
            label: key.split('_').map(word => 
                word.charAt(0).toUpperCase() + word.slice(1)
            ).join(' ')
        }))
        : []

    const getFilteredData = () => {
        if (!loggingData?.logs) return { data: [], totalItems: 0, totalPages: 0 }
        
        let filtered = [...loggingData.logs]

        filtered = filtered.reduce((acc, current) => {
            const timestamp = new Date(current.created_at).getTime();
            
            const similar = acc.filter(item => 
                Math.abs(new Date(item.created_at).getTime() - timestamp) < 1000 && 
                item.event_type === current.event_type &&
                item.channel_id === current.channel_id
            );

            if ('details' in current.content && 
                typeof current.content.details === 'string' && 
                current.content.details.includes('messages deleted')) {
                acc = acc.filter(item => !similar.includes(item));
                acc.push(current);
                return acc;
            }

            if (similar.some(item => 
                'details' in item.content && 
                typeof item.content.details === 'string' && 
                item.content.details.includes('messages deleted'))) {
                return acc;
            }

            if (!similar.length) {
                acc.push(current);
            }
            
            return acc;
        }, [] as typeof filtered);

        if (selectedChannel) {
            filtered = filtered.filter(log => 
                log.channel_id === selectedChannel.value
            )
        }

        if (selectedEvent) {
            filtered = filtered.filter(log => 
                log.event_type === selectedEvent.value
            )
        }

        if (searchQuery.trim()) {
            filtered = filtered.filter(log => {
                const userId = ('user' in log.content && log.content.user?.id) || 
                              ('author' in log.content && log.content.author?.id) ||
                              ('member' in log.content && log.content.member?.id);
                
                return (userId && userId.includes(searchQuery)) ||
                       log.event_type.toLowerCase().includes(searchQuery.toLowerCase())
            })
        }

        filtered.sort((a, b) => 
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )

        return {
            data: filtered.slice(
                (currentPage - 1) * itemsPerPage,
                currentPage * itemsPerPage
            ),
            totalItems: filtered.length,
            totalPages: Math.ceil(filtered.length / itemsPerPage)
        }
    }

    const filteredData = getFilteredData()

    if (!loggingData?.enabled) {
        return (
            <div className="space-y-6">
                <div>
                    <h1 className="text-xl md:text-2xl font-bold text-white">Server Logs</h1>
                    <p className="text-white/60">Logging is not enabled for this server</p>
                </div>
            </div>
        )
    }

    function getUserFromContent(content: LogEntry['content']) {
        let userId = null;
        
        if ('author' in content && content.author) {
            userId = content.author.id;
        } else if ('user' in content && content.user) {
            userId = content.user.id;
        } else if ('member' in content && content.member) {
            userId = content.member.id;
        }

        if (userId && users[userId]) {
            return {
                name: users[userId].name,
                bot: users[userId].bot
            }
        }
        return null;
    }

    function getChannelFromContent(content: LogEntry['content']) {
        if ('channel' in content) {
            return content.channel.name ? `#${content.channel.name}` : content.channel.id
        }
        return null
    }

    function getDetailsFromContent(content: LogEntry['content']): string {
        if ('details' in content && typeof content.details === 'string') {
            return content.details
        }
        if ('message' in content && 'changes' in content.message) {
            const messageContent = content as MessageEditContent
            return `Message edited in #${messageContent.channel.name}`
        }
        if ('changes' in content) {
            const changes = (content as RoleUpdateContent | ChannelUpdateContent).changes
            if ('name' in changes && changes.name) {
                return `Name changed from "${changes.name.before}" to "${changes.name.after}"`
            }
        }
        return '-'
    }

    function formatDiscordText(text: string, users: Record<string, { name: string | null; bot: boolean | null }>, channels: Record<string, { name: string; type: string }>) {
        return text
            .replace(/<@!?(\d+)>/g, (match, userId) => {
                const user = users[userId];
                return user ? `<span class="text-blue-400">@${user.name}</span>` : match;
            })
            .replace(/<#(\d+)>/g, (match, channelId) => {
                const channel = channels[channelId];
                return channel ? `<span class="text-teal-400">#${channel.name}</span>` : match;
            });
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-xl md:text-2xl font-bold text-white">Server Logs</h1>
                <p className="text-white/60">View your server&apos;s audit logs and events</p>
            </div>

            <div className="overflow-x-auto">
                <div className="min-w-[800px]">
                    <div className="bg-[#111111] rounded-xl border border-[#222222] p-4 space-y-4">
                        <div className="flex flex-row gap-4">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-500" />
                                <input 
                                    type="text"
                                    placeholder="Search logs..."
                                    className="w-full bg-[#0B0C0C] text-sm rounded-xl pl-9 pr-4 h-[42px] border border-[#222222] focus:outline-none focus:border-[#333333] placeholder-zinc-500 text-white"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                />
                            </div>

                            <Select
                                className="w-[200px]"
                                classNames={{
                                    control: () => 'bg-[#0B0C0C] border border-[#222222] rounded-xl !min-h-0 h-[42px] !cursor-pointer hover:border-[#333333]',
                                    menu: () => 'bg-[#0B0C0C] border border-[#222222] rounded-xl mt-1',
                                    option: (state) => `px-3 py-2 hover:bg-[#151515] ${state.isFocused ? 'bg-[#151515]' : ''} text-white`,
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
                                options={eventOptions}
                                value={selectedEvent}
                                onChange={setSelectedEvent}
                                placeholder="All Events"
                                components={{
                                    IndicatorSeparator: () => null
                                }}
                                isClearable
                            />
                        </div>

                        <div className="flex flex-row gap-4">
                            <Select
                                className="flex-1"
                                classNames={{
                                    control: () => 'bg-[#0B0C0C] border border-[#222222] rounded-xl !min-h-0 h-[42px] !cursor-pointer hover:border-[#333333]',
                                    menu: () => 'bg-[#0B0C0C] border border-[#222222] rounded-xl mt-1',
                                    option: (state) => `px-3 py-2 hover:bg-[#151515] ${state.isFocused ? 'bg-[#151515]' : ''} text-white`,
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
                                options={channelOptions}
                                value={selectedChannel}
                                onChange={setSelectedChannel}
                                placeholder="All Channels"
                                components={{
                                    IndicatorSeparator: () => null
                                }}
                                isClearable
                            />
                        </div>
                    </div>
                </div>
            </div>

            <div className="overflow-x-auto">
                <div className="min-w-[800px]">
                    <div className="bg-[#111111] rounded-xl border border-[#222222] overflow-hidden">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-[#222222]">
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Event</th>
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Channel</th>
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">User</th>
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Details</th>
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Date</th>
                                    <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm"></th>
                                </tr>
                            </thead>
                            <tbody className="text-xs md:text-sm">
                                {isLoading ? (
                                    [...Array(5)].map((_, i) => (
                                        <tr key={i} className="border-t border-[#222222]">
                                            <td className="py-3 px-4">
                                                <div className="w-20 h-6 bg-white/5 rounded-md animate-pulse" />
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="w-24 h-4 bg-white/5 rounded-md animate-pulse" />
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="w-28 h-4 bg-white/5 rounded-md animate-pulse" />
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="w-48 h-4 bg-white/5 rounded-md animate-pulse" />
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="w-32 h-4 bg-white/5 rounded-md animate-pulse" />
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="w-8 h-8 bg-white/5 rounded-lg animate-pulse" />
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    filteredData.data.map((log) => (
                                        <tr key={log.id} className="border-t border-[#222222] hover:bg-[#151515]">
                                            <td className="py-3 px-4">
                                                <span className="px-2 py-1 rounded-md text-xs bg-white/10 text-white">
                                                    {log.event_type}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-zinc-400">
                                                {log.channel_id && channels[log.channel_id]?.name 
                                                    ? `#${channels[log.channel_id].name}` 
                                                    : '-'}
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-2">
                                                    {(() => {
                                                        const user = getUserFromContent(log.content);
                                                        return user && (
                                                            <span className="text-white">
                                                                {user.name}
                                                                {user.bot && (
                                                                    <span className="ml-1 px-1 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-500">BOT</span>
                                                                )}
                                                            </span>
                                                        )
                                                    })()}
                                                </div>
                                            </td>
                                            <td className="py-3 px-4 text-zinc-400">
                                                <div 
                                                    className="truncate max-w-[300px] [&_a]:text-blue-400 [&_a]:hover:underline [&_strong]:font-semibold [&_em]:italic"
                                                    dangerouslySetInnerHTML={{ 
                                                        __html: ('details' in log.content && typeof log.content.details === 'string')
                                                            ? formatDiscordText(log.content.details, users, channels)
                                                                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                                                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                                                                .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
                                                            : getDetailsFromContent(log.content) || '-'
                                                    }}
                                                />
                                            </td>
                                            <td className="py-3 px-4 text-zinc-400">
                                                {format(new Date(log.created_at), "MMM d, yyyy HH:mm")}
                                            </td>
                                            <td className="py-3 px-4">
                                                <button
                                                    onClick={() => setSelectedLog(log)}
                                                    className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                                                >
                                                    <Eye className="w-4 h-4 text-white/40" />
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>

                        {(!isLoading && !loggingData || filteredData.data.length === 0) && (
                            <div className="text-center py-8 text-zinc-400">
                                {!loggingData ? "Loading logs..." : "No logs available."}
                            </div>
                        )}
                    </div>

                    <div className="flex flex-col sm:flex-row items-center justify-between border-t border-[#222222] px-4 py-3 gap-4">
                        <div>
                            <p className="text-xs md:text-sm text-zinc-400 text-center sm:text-left">
                                Showing <span className="font-medium text-white">
                                    {filteredData.data.length > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0}
                                </span> to{' '}
                                <span className="font-medium text-white">
                                    {Math.min(currentPage * itemsPerPage, filteredData.totalItems)}
                                </span> of{' '}
                                <span className="font-medium text-white">{filteredData.totalItems}</span> results
                            </p>
                        </div>
                        {filteredData.totalPages > 1 && (
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
                                        onClick={() => setCurrentPage(page => Math.min(filteredData.totalPages, page + 1))}
                                        disabled={currentPage === filteredData.totalPages}
                                        className="relative inline-flex items-center rounded-r-md border border-[#222222] bg-[#0B0C0C] px-2 py-2 text-sm font-medium text-white hover:bg-[#151515] disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <span className="sr-only">Next</span>
                                        <ChevronRight className="h-5 w-5" aria-hidden="true" />
                                    </button>
                                </nav>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <LogDetailsModal 
            // @ts-ignore
                log={selectedLog}
                onClose={() => setSelectedLog(null)}
            />
        </div>
    )
} 