"use client"

import { fetchGuildSettings } from "@/libs/dashboard/adminGuild"
import { useMutation } from "@tanstack/react-query"
import { Search, Users, Crown, Calendar, Check, ChevronLeft, ChevronRight } from "lucide-react"
import { useState, useEffect } from "react"
import { format } from "date-fns"
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import { useRouter } from "next/navigation"

export default function ServerLookup() {
    const router = useRouter()
    const [isReady, setIsReady] = useState(false)
    const [guildId, setGuildId] = useState("")
    const [currentPage, setCurrentPage] = useState(1)
    const itemsPerPage = 30
    
    useEffect(() => {
        setTimeout(() => setIsReady(true), 100)
    }, [])
    
    const { mutate: fetchSettings, data: settings, isPending, error } = useMutation({
        mutationFn: fetchGuildSettings,
        throwOnError: true
    })

    useEffect(() => {
        if (error?.message === "403") {
            router.push('/')
        }
    }, [error, router])

    if (!isReady || isPending) {
        return (
            <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
                <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-white border-r-2 border-b-2 border-transparent mb-4"></div>
                    <h2 className="text-xl font-semibold text-white">Loading server lookup...</h2>
                    <p className="text-white/60 mt-2">Please wait while we fetch your data</p>
                </div>
            </div>
        )
    }

    const paginatedCommands = settings?.recent_commands
        ? settings.recent_commands.slice(
            (currentPage - 1) * itemsPerPage,
            currentPage * itemsPerPage
          )
        : []
    
    const totalPages = settings?.recent_commands
        ? Math.ceil(settings.recent_commands.length / itemsPerPage)
        : 0

    return (
        <div>
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-white">Server Lookup</h1>
                <p className="text-white/60 mt-2">Look up settings for any server</p>
            </div>

            <div className="bg-[#0A0A0B] rounded-xl border border-white/5 p-6">
                <div className="flex gap-3">
                    <input
                        type="text"
                        placeholder="Enter server ID..."
                        value={guildId}
                        onChange={(e) => setGuildId(e.target.value)}
                        className="flex-1 bg-black/20 text-sm rounded-lg px-4 h-[38px] border border-white/5 focus:outline-none focus:border-white/10 placeholder-white/40 text-white"
                    />
                    <button
                        onClick={() => fetchSettings(guildId)}
                        disabled={!guildId || isPending}
                        className="flex items-center gap-2 px-4 bg-white/5 hover:bg-white/10 disabled:opacity-50 disabled:hover:bg-white/5 text-white rounded-lg"
                    >
                        <Search className="w-4 h-4" />
                        Search
                    </button>
                </div>

                {isPending && (
                    <div className="text-white/60 mt-4">Loading settings...</div>
                )}

                {error && (
                    <div className="text-red-400 mt-4">
                        {error instanceof Error ? error.message : "Failed to fetch settings"}
                    </div>
                )}

                {settings && (
                    <div className="mt-6 space-y-6">
                        <div className="flex items-start gap-6">
                            {settings.guild.icon && (
                                <img 
                                    src={settings.guild.icon} 
                                    alt={settings.guild.name}
                                    className="w-20 h-20 rounded-xl"
                                />
                            )}
                            <div className="flex-1">
                                <h2 className="text-xl font-semibold text-white">{settings.guild.name}</h2>
                                <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div className="flex items-center gap-2 text-white/60">
                                        <Users className="w-4 h-4" />
                                        <span>{settings.guild.member_count.toLocaleString()} members</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/60">
                                        <Crown className="w-4 h-4" />
                                        <span>Owner: {settings.guild.owner_id}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/60">
                                        <Calendar className="w-4 h-4" />
                                        <span>Created: {format(new Date(settings.guild.created_at), 'MMM d, yyyy')}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-black/20 rounded-lg p-4">
                                <h3 className="text-white font-medium mb-3">Features</h3>
                                <div className="flex flex-wrap gap-2">
                                    {settings.guild.features.map(feature => (
                                        <span 
                                            key={feature} 
                                            className="px-2 py-1 rounded text-xs bg-white/5 text-white/80"
                                        >
                                            {feature}
                                        </span>
                                    ))}
                                </div>
                            </div>
                            <div className="bg-black/20 rounded-lg p-4">
                                <h3 className="text-white font-medium mb-3">Basic Settings</h3>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>SafeSearch: {settings.settings.safesearch_level}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Transcription: {settings.settings.transcription ? 'Enabled' : 'Disabled'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Welcome Removal: {settings.settings.welcome_removal ? 'Enabled' : 'Disabled'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Reskin: {settings.settings.reskin ? 'Enabled' : 'Disabled'}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-black/20 rounded-lg p-4">
                                <h3 className="text-white font-medium mb-3">Reposter Settings</h3>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Prefix: {settings.settings.reposter.prefix ? 'Enabled' : 'Disabled'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Delete: {settings.settings.reposter.delete ? 'Enabled' : 'Disabled'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Embed: {settings.settings.reposter.embed ? 'Enabled' : 'Disabled'}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-black/20 rounded-lg p-4">
                                <h3 className="text-white font-medium mb-3">Verification Settings</h3>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Channel: {settings.settings.verification.channel_id || 'Not Set'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Role: {settings.settings.verification.role_id || 'Not Set'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>VPN Check: {settings.settings.verification.vpn_check ? 'Enabled' : 'Disabled'}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-black/20 rounded-lg p-4">
                                <h3 className="text-white font-medium mb-3">Play Settings</h3>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Panel: {settings.settings.play.panel ? 'Enabled' : 'Disabled'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-white/80">
                                        <Check className="w-4 h-4" />
                                        <span>Deletion: {settings.settings.play.deletion ? 'Enabled' : 'Disabled'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-black/20 rounded-lg overflow-hidden">
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="border-b border-white/5 bg-black/20">
                                            <th className="text-left py-3 px-4 font-medium text-white/60 text-sm">Command</th>
                                            <th className="text-left py-3 px-4 font-medium text-white/60 text-sm">Category</th>
                                            <th className="text-left py-3 px-4 font-medium text-white/60 text-sm">User ID</th>
                                            <th className="text-left py-3 px-4 font-medium text-white/60 text-sm">Timestamp</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {paginatedCommands.map((cmd, index) => (
                                            <tr key={index} className="border-t border-white/5 hover:bg-white/[0.02]">
                                                <td className="py-3 px-4 text-white text-sm">{cmd.command}</td>
                                                <td className="py-3 px-4">
                                                    <span className="px-2 py-1 rounded text-xs bg-white/5 text-white">
                                                        {cmd.category}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4 text-white text-sm">{cmd.user_id}</td>
                                                <td className="py-3 px-4 text-white/60 text-sm">
                                                    {format(new Date(cmd.timestamp), 'MMM d, yyyy HH:mm:ss')}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {settings?.recent_commands && settings.recent_commands.length > 0 && (
                                <div className="flex flex-col sm:flex-row items-center justify-between border-t border-white/5 px-4 py-3 gap-4">
                                    <div>
                                        <p className="text-sm text-white/60 text-center sm:text-left">
                                            Showing <span className="font-medium text-white">{((currentPage - 1) * itemsPerPage) + 1}</span> to{' '}
                                            <span className="font-medium text-white">
                                                {Math.min(currentPage * itemsPerPage, settings.recent_commands.length)}
                                            </span> of{' '}
                                            <span className="font-medium text-white">{settings.recent_commands.length}</span> results
                                        </p>
                                    </div>
                                    {totalPages > 1 && (
                                        <div className="flex justify-center sm:justify-end w-full sm:w-auto">
                                            <nav className="inline-flex rounded-lg border border-white/5 overflow-hidden" aria-label="Pagination">
                                                <button
                                                    onClick={() => setCurrentPage(page => Math.max(1, page - 1))}
                                                    disabled={currentPage === 1}
                                                    className="px-3 py-2 text-sm text-white hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed border-r border-white/5"
                                                >
                                                    <ChevronLeft className="h-4 w-4" />
                                                </button>
                                                <button
                                                    onClick={() => setCurrentPage(page => Math.min(totalPages, page + 1))}
                                                    disabled={currentPage === totalPages}
                                                    className="px-3 py-2 text-sm text-white hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
                                                >
                                                    <ChevronRight className="h-4 w-4" />
                                                </button>
                                            </nav>
                                        </div>
                                    )}
                                </div>
                            )}

                            {(!settings?.recent_commands || settings.recent_commands.length === 0) && (
                                <div className="text-center py-8 text-white/60">
                                    No recent commands available.
                                </div>
                            )}
                        </div>

                        <div className="bg-black/20 p-4 rounded-lg">
                            <h3 className="text-white font-medium mb-3">Raw Data</h3>
                            <div className="rounded-lg overflow-hidden">
                                <div style={{ maxHeight: '500px', overflow: 'auto' }}>
                                    <SyntaxHighlighter 
                                        language="json"
                                        style={vscDarkPlus}
                                        customStyle={{
                                            margin: 0,
                                            background: '#0A0A0B',
                                            fontSize: '13px'
                                        }}
                                    >
                                        {JSON.stringify(settings, null, 2)}
                                    </SyntaxHighlighter>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
} 