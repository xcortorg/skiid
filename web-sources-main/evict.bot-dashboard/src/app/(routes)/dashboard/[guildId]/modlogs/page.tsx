"use client"

import { fetchGuildModLogs, ModCase } from "@/libs/dashboard/guild/modlogs"
import { useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import { ChevronLeft, ChevronRight, Eye, Search, Shield, Beaker } from "lucide-react"
import { useEffect, useState } from "react"
import Select from "react-select"
import CaseDetailsModal from "../components/modlogs/CaseDetailsModal"
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

function PermissionDenied() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            <div className="bg-red-500/10 p-2 rounded-full mb-4">
                <Shield className="w-8 h-8 text-red-500" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
            <p className="text-white/60 max-w-md">
                Only the server owner can access the moderation logs.
            </p>
        </div>
    )
}

export default function ModLogsPage({ params }: { params: { guildId: string } }) {
    const [selectedCase, setSelectedCase] = useState<ModCase | null>(null)
    const [currentPage, setCurrentPage] = useState(1)
    const [searchQuery, setSearchQuery] = useState("")
    const [selectedAction, setSelectedAction] = useState<string>("")
    const [selectedUser, setSelectedUser] = useState<any>(null)
    const [selectedModerator, setSelectedModerator] = useState<any>(null)
    const router = useRouter()

    const { data: betaAccess } = useQuery({
        queryKey: ["beta"],
        queryFn: checkBetaAccess,
        staleTime: 1000 * 60 * 15
    })

    const { data: modlogs } = useQuery({
        queryKey: ["modlogs", params.guildId],
        queryFn: () => fetchGuildModLogs(params.guildId),
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

    useEffect(() => {
        setCurrentPage(1)
    }, [searchQuery, selectedAction, selectedUser, selectedModerator])

    if (!betaAccess?.has_access) {
        return <BetaAccessRequired />
    }

    const itemsPerPage = 30

    const actionOptions = [
        { value: "", label: "All Actions" },
        { value: "ban", label: "Ban" },
        { value: "unban", label: "Unban" },
        { value: "kick", label: "Kick" },
        { value: "mute", label: "Mute" },
        { value: "unmute", label: "Unmute" },
        { value: "timeout", label: "Timeout" },
        { value: "untimeout", label: "Untimeout" },
        { value: "warn", label: "Warn" },
        { value: "role add", label: "Role Add" },
        { value: "role remove", label: "Role Remove" },
        { value: "hardban", label: "Hard Ban" },
        { value: "hardunban", label: "Hard Unban" },
        { value: "spam filter", label: "Spam Filter" }
    ]

    const getUserOptions = () => {
        return (
            modlogs?.users.map(user => ({
                value: user.user_id,
                label: `${user.user_displayname} (@${user.user_name})`,
                avatar: user.user_avatar
            })) || []
        )
    }

    const getPaginatedData = () => {
        if (!modlogs?.cases) return { data: [], totalItems: 0, totalPages: 0 }

        const startIndex = (currentPage - 1) * itemsPerPage
        const endIndex = startIndex + itemsPerPage

        return {
            data: modlogs.cases.slice(startIndex, endIndex),
            totalItems: modlogs.cases.length,
            totalPages: Math.ceil(modlogs.cases.length / itemsPerPage)
        }
    }

    const paginatedData = getPaginatedData()

    const findUser = (userId: string | number) => {
        const searchId = typeof userId === "number" ? userId.toString() : userId
        return modlogs?.users.find(user => user.user_id === searchId)
    }

    const getFilteredData = () => {
        if (!modlogs?.cases) return { data: [], totalItems: 0, totalPages: 0 }

        let filtered = [...modlogs.cases] 

        if (selectedAction) {
            filtered = filtered.filter(
                case_ => case_.action.toLowerCase() === selectedAction.toLowerCase()
            )
        }

        if (selectedUser) {
            filtered = filtered.filter(case_ => case_.user_id.toString() === selectedUser.value)
        }

        if (selectedModerator) {
            filtered = filtered.filter(
                case_ => case_.moderator_id.toString() === selectedModerator.value
            )
        }

        if (searchQuery.trim()) {
            filtered = filtered.filter(case_ =>
                case_.reason?.toLowerCase().includes(searchQuery.toLowerCase())
            )
        }

        filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

        const startIndex = (currentPage - 1) * itemsPerPage
        const endIndex = startIndex + itemsPerPage

        return {
            data: filtered.slice(startIndex, endIndex),
            totalItems: filtered.length,
            totalPages: Math.ceil(filtered.length / itemsPerPage)
        }
    }

    const filteredData = getFilteredData()

    if (modlogs && !modlogs.enabled) {
        return (
            <div className="space-y-6">
                <div className="animate-pulse space-y-2">
                    <div className="bg-white/5 h-8 w-32 rounded" />
                    <div className="bg-white/5 h-5 w-64 rounded" />
                </div>

                <div className="bg-[#111111] rounded-xl border border-[#222222] overflow-hidden">
                    <div className="animate-pulse">
                        <div className="bg-white/5 h-12 w-full" />
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="bg-white/5 h-16 w-full mt-px" />
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-xl md:text-2xl font-bold text-white">Moderation Logs</h1>
                <p className="text-white/60">
                    View and manage your server&apos;s moderation history
                </p>
            </div>

            <div className="bg-[#111111] rounded-xl border border-[#222222] p-4 space-y-4">
                <div className="flex flex-col sm:flex-row gap-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-500" />
                        <input
                            type="text"
                            placeholder="Search by reason..."
                            className="w-full bg-[#0B0C0C] text-sm rounded-xl pl-9 pr-4 h-[42px] border border-[#222222] focus:outline-none focus:border-[#333333] placeholder-zinc-500 text-white"
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                        />
                    </div>

                    <Select
                        className="w-full sm:w-[200px]"
                        classNames={{
                            control: () =>
                                "bg-[#0B0C0C] border border-[#222222] rounded-xl !min-h-0 h-[42px] !cursor-pointer hover:border-[#333333]",
                            menu: () => "bg-[#0B0C0C] border border-[#222222] rounded-xl mt-1",
                            option: state =>
                                `px-3 py-2 hover:bg-[#151515] ${state.isFocused ? "bg-[#151515]" : ""} text-white`,
                            placeholder: () => "text-zinc-500",
                            singleValue: () => "text-white",
                            input: () => "text-white",
                            menuList: () => "py-2"
                        }}
                        styles={{
                            control: base => ({
                                ...base,
                                boxShadow: "none",
                                backgroundColor: "#0B0C0C",
                                borderColor: "#222222",
                                "&:hover": {
                                    borderColor: "#333333"
                                }
                            }),
                            menu: base => ({
                                ...base,
                                backgroundColor: "#0B0C0C",
                                overflow: "hidden"
                            }),
                            option: base => ({
                                ...base,
                                backgroundColor: "transparent"
                            })
                        }}
                        options={actionOptions}
                        value={actionOptions.find(opt => opt.value === selectedAction)}
                        onChange={(option: any) => setSelectedAction(option?.value || "")}
                        placeholder="All Actions"
                        components={{
                            IndicatorSeparator: () => null
                        }}
                    />
                </div>

                <div className="flex flex-col sm:flex-row gap-4">
                    <Select
                        className="flex-1"
                        classNames={{
                            control: () =>
                                "bg-[#0B0C0C] border border-[#222222] rounded-xl !min-h-0 h-[42px] !cursor-pointer hover:border-[#333333]",
                            menu: () => "bg-[#0B0C0C] border border-[#222222] rounded-xl mt-1",
                            option: state =>
                                `px-3 py-2 hover:bg-[#151515] ${state.isFocused ? "bg-[#151515]" : ""} text-white`,
                            placeholder: () => "text-zinc-500",
                            singleValue: () => "text-white",
                            input: () => "text-white",
                            menuList: () => "py-2"
                        }}
                        styles={{
                            control: base => ({
                                ...base,
                                boxShadow: "none",
                                backgroundColor: "#0B0C0C",
                                borderColor: "#222222",
                                "&:hover": {
                                    borderColor: "#333333"
                                }
                            }),
                            menu: base => ({
                                ...base,
                                backgroundColor: "#0B0C0C",
                                overflow: "hidden"
                            }),
                            option: base => ({
                                ...base,
                                backgroundColor: "transparent"
                            })
                        }}
                        options={getUserOptions()}
                        value={selectedUser}
                        onChange={setSelectedUser}
                        placeholder="Filter by User"
                        components={{
                            IndicatorSeparator: () => null
                        }}
                        isSearchable
                        isClearable
                    />

                    <Select
                        className="flex-1"
                        classNames={{
                            control: () =>
                                "bg-[#0B0C0C] border border-[#222222] rounded-xl !min-h-0 h-[42px] !cursor-pointer hover:border-[#333333]",
                            menu: () => "bg-[#0B0C0C] border border-[#222222] rounded-xl mt-1",
                            option: state =>
                                `px-3 py-2 hover:bg-[#151515] ${state.isFocused ? "bg-[#151515]" : ""} text-white`,
                            placeholder: () => "text-zinc-500",
                            singleValue: () => "text-white",
                            input: () => "text-white",
                            menuList: () => "py-2"
                        }}
                        styles={{
                            control: base => ({
                                ...base,
                                boxShadow: "none",
                                backgroundColor: "#0B0C0C",
                                borderColor: "#222222",
                                "&:hover": {
                                    borderColor: "#333333"
                                }
                            }),
                            menu: base => ({
                                ...base,
                                backgroundColor: "#0B0C0C",
                                overflow: "hidden"
                            }),
                            option: base => ({
                                ...base,
                                backgroundColor: "transparent"
                            })
                        }}
                        options={getUserOptions()}
                        value={selectedModerator}
                        onChange={setSelectedModerator}
                        placeholder="Filter by Moderator"
                        components={{
                            IndicatorSeparator: () => null
                        }}
                        isSearchable
                        isClearable
                    />
                </div>
            </div>

            <div className="bg-[#111111] rounded-xl border border-[#222222] overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full min-w-[800px]">
                        <thead>
                            <tr className="border-b border-[#222222]">
                                <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Case ID</th>
                                <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">User</th>
                                <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Action</th>
                                <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Moderator</th>
                                <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm">Date</th>
                                <th className="text-left py-3 px-4 font-medium text-zinc-400 text-xs md:text-sm"></th>
                            </tr>
                        </thead>
                        <tbody className="text-xs md:text-sm">
                            {filteredData.data.map((case_) => (
                                <tr key={case_.id} className="border-t border-[#222222] hover:bg-[#151515]">
                                    <td className="py-3 px-4">#{case_.case_id}</td>
                                    <td className="py-3 px-4">
                                        <div className="flex items-center gap-2">
                                            <img 
                                                src={findUser(case_.user_id)?.user_avatar || "https://cdn.discordapp.com/embed/avatars/0.png"}
                                                alt={findUser(case_.user_id)?.user_displayname || "Unknown"}
                                                className="w-6 h-6 rounded-full"
                                            />
                                            <span>
                                                {findUser(case_.user_id)?.user_displayname || "Unknown"}{' '}
                                                <span className="text-zinc-400">@{findUser(case_.user_id)?.user_name || "Unknown"}</span>
                                            </span>
                                        </div>
                                    </td>
                                    <td className="py-3 px-4">
                                        <span className={`px-2 py-1 rounded-md text-xs ${getActionColor(case_.action)}`}>
                                            {case_.action}
                                        </span>
                                    </td>
                                    <td className="py-3 px-4">
                                        <div className="flex items-center gap-2">
                                            <img 
                                                src={findUser(case_.moderator_id)?.user_avatar || "https://cdn.discordapp.com/embed/avatars/0.png"}
                                                alt={findUser(case_.moderator_id)?.user_displayname || "Unknown"}
                                                className="w-6 h-6 rounded-full"
                                            />
                                            <span>
                                                {findUser(case_.moderator_id)?.user_displayname || "Unknown"}{' '}
                                                <span className="text-zinc-400">@{findUser(case_.moderator_id)?.user_name || "Unknown"}</span>
                                            </span>
                                        </div>
                                    </td>
                                    <td className="py-3 px-4 text-zinc-400">
                                        {format(new Date(case_.timestamp), "MMM d, yyyy")}
                                    </td>
                                    <td className="py-3 px-4">
                                        <button
                                            onClick={() => setSelectedCase(case_)}
                                            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                                        >
                                            <Eye className="w-4 h-4 text-white/40" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {(modlogs && !modlogs.enabled) && (
                    <div className="text-center py-8 text-zinc-400">
                        Loading moderation logs...
                    </div>
                )}
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between border-t border-[#222222] px-4 py-3 gap-4">
                <div>
                    <p className="text-xs md:text-sm text-zinc-400 text-center sm:text-left">
                        Showing{" "}
                        <span className="font-medium text-white">
                            {filteredData.data.length > 0
                                ? (currentPage - 1) * itemsPerPage + 1
                                : 0}
                        </span>{" "}
                        to{" "}
                        <span className="font-medium text-white">
                            {Math.min(currentPage * itemsPerPage, filteredData.totalItems)}
                        </span>{" "}
                        of <span className="font-medium text-white">{filteredData.totalItems}</span>{" "}
                        results
                    </p>
                </div>
                {filteredData.totalPages > 1 && (
                    <div className="flex justify-center sm:justify-end w-full sm:w-auto">
                        <nav
                            className="isolate inline-flex -space-x-px rounded-md shadow-sm"
                            aria-label="Pagination">
                            <button
                                onClick={() => setCurrentPage(page => Math.max(1, page - 1))}
                                disabled={currentPage === 1}
                                className="relative inline-flex items-center rounded-l-md border border-[#222222] bg-[#0B0C0C] px-2 py-2 text-sm font-medium text-white hover:bg-[#151515] disabled:opacity-50 disabled:cursor-not-allowed">
                                <span className="sr-only">Previous</span>
                                <ChevronLeft className="h-5 w-5" aria-hidden="true" />
                            </button>
                            <button
                                onClick={() =>
                                    setCurrentPage(page =>
                                        Math.min(filteredData.totalPages, page + 1)
                                    )
                                }
                                disabled={currentPage === filteredData.totalPages}
                                className="relative inline-flex items-center rounded-r-md border border-[#222222] bg-[#0B0C0C] px-2 py-2 text-sm font-medium text-white hover:bg-[#151515] disabled:opacity-50 disabled:cursor-not-allowed">
                                <span className="sr-only">Next</span>
                                <ChevronRight className="h-5 w-5" aria-hidden="true" />
                            </button>
                        </nav>
                    </div>
                )}
            </div>

            {selectedCase && (
                <CaseDetailsModal
                    case_={selectedCase}
                    user={findUser(selectedCase.user_id)}
                    moderator={findUser(selectedCase.moderator_id)}
                    onClose={() => setSelectedCase(null)}
                />
            )}
        </div>
    )
}

function getActionColor(action: string) {
    switch (action.toLowerCase()) {
        case "ban":
            return "bg-red-500/10 text-red-500"
        case "kick":
            return "bg-orange-500/10 text-orange-500"
        case "mute":
        case "timeout":
            return "bg-yellow-500/10 text-yellow-500"
        case "warn":
            return "bg-blue-500/10 text-blue-500"
        case "role add":
        case "role remove":
            return "bg-purple-500/10 text-purple-500"
        default:
            return "bg-white/10 text-white"
    }
}
