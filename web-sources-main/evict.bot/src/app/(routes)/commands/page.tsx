"use client"

import { Categories, Commands } from "@/data/Commands"
import { Command } from "@/types/Command"
import { AnimatePresence, motion } from "framer-motion"
import { ChevronDown, ChevronUp, Copy, ExternalLink, Filter, Search, X } from "lucide-react"
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
import toast, { Toaster } from "react-hot-toast"

const ITEMS_PER_LOAD = 12

const CommandsPage = () => {
    const [visibleItems, setVisibleItems] = useState(ITEMS_PER_LOAD)
    const [activeCategory, setActiveCategory] = useState<string>("All")
    const [searchQuery, setSearchQuery] = useState("")
    const [selectedCommand, setSelectedCommand] = useState<Command | null>(null)
    const [showFilters, setShowFilters] = useState(false)
    const filterRef = useRef<HTMLDivElement>(null)
    const modalRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
                setShowFilters(false)
            }
        }
        document.addEventListener("mousedown", handleClickOutside)
        return () => {
            document.removeEventListener("mousedown", handleClickOutside)
        }
    }, [])

    useEffect(() => {
        if (selectedCommand) {
            document.body.style.overflow = "hidden"
        } else {
            document.body.style.overflow = ""
        }

        return () => {
            document.body.style.overflow = ""
        }
    }, [selectedCommand])

    const filteredCommands = useMemo(() => {
        return Commands.filter(command => {
            if (activeCategory !== "All" && command.category !== activeCategory) {
                return false
            }

            if (searchQuery.trim() === "") {
                return true
            }

            const query = searchQuery.toLowerCase()
            return (
                command.name.toLowerCase().includes(query) ||
                command.description.toLowerCase().includes(query) ||
                command.aliases?.some(alias => alias.toLowerCase().includes(query))
            )
        })
    }, [activeCategory, searchQuery])

    const loadMore = useCallback(() => {
        setVisibleItems(prev => prev + ITEMS_PER_LOAD)
    }, [])

    const visibleCommands = useMemo(
        () => filteredCommands.slice(0, visibleItems),
        [filteredCommands, visibleItems]
    )

    const getCategoryCount = useCallback((categoryName: string) => {
        if (categoryName === "All") {
            return Commands.length
        }
        return Commands.filter(cmd => cmd.category === categoryName).length
    }, [])

    const copyCommand = useCallback(async (command: string) => {
        try {
            await navigator.clipboard.writeText(command)
            toast.success("Command copied to clipboard!", {
                style: {
                    background: "rgba(15, 15, 20, 0.9)",
                    color: "rgba(255, 255, 255, 0.9)",
                    backdropFilter: "blur(10px)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)"
                },
                duration: 2000
            })
        } catch (err) {
            toast.error("Failed to copy command", {
                style: {
                    background: "rgba(15, 15, 20, 0.9)",
                    color: "rgba(255, 255, 255, 0.9)",
                    backdropFilter: "blur(10px)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)"
                }
            })
        }
    }, [])

    const handleModalKeyDown = useCallback(
        (e: KeyboardEvent) => {
            if (e.key === "Escape" && selectedCommand) {
                setSelectedCommand(null)
            }
        },
        [selectedCommand]
    )

    useEffect(() => {
        document.addEventListener("keydown", handleModalKeyDown)
        return () => {
            document.removeEventListener("keydown", handleModalKeyDown)
        }
    }, [handleModalKeyDown])

    const memoizedBackgroundElements = useMemo(
        () => (
            <>
                <div className="absolute inset-0 z-0 bg-[#080808]" />

                <div
                    className="absolute inset-0 z-1 w-screen h-screen overflow-hidden pointer-events-none"
                    style={{ willChange: "transform", transform: "translateZ(0)" }}>
                    <div className="absolute w-[210vw] h-[50vh] -top-[25vh] -left-[5vw] bg-gradient-to-b from-blue-600/15 to-transparent blur-[80px] transform animate-wave-slow will-change-transform"></div>

                    <div className="absolute w-[200vw] h-[60vh] top-[20vh] -left-[10vw] bg-gradient-to-b from-indigo-600/12 to-transparent blur-[90px] transform animate-wave-medium will-change-transform"></div>

                    <div className="absolute w-[190vw] h-[45vh] top-[60vh] left-[5vw] bg-gradient-to-b from-purple-600/15 to-slate-700/10 blur-[80px] transform animate-wave-fast will-change-transform"></div>
                </div>

                <div
                    className="absolute inset-0 z-2 pointer-events-none opacity-[0.03]"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                        backgroundRepeat: "repeat",
                        width: "100%",
                        height: "100%"
                    }}
                />

                <div
                    className="absolute inset-0 z-3 w-screen h-screen overflow-hidden opacity-30 pointer-events-none"
                    style={{ willChange: "transform", transform: "translateZ(0)" }}>
                    <div className="absolute -top-[40%] -left-[20%] w-[70%] h-[70%] bg-blue-500/15 rounded-full blur-[120px] animate-blob animation-delay-0s"></div>
                    <div className="absolute -bottom-[30%] -right-[20%] w-[60%] h-[60%] bg-purple-500/15 rounded-full blur-[120px] animate-blob animation-delay-2s"></div>
                    <div className="absolute top-[20%] right-[10%] w-[50%] h-[50%] bg-pink-500/15 rounded-full blur-[120px] animate-blob animation-delay-4s"></div>
                </div>
            </>
        ),
        []
    )

    const renderCommandCard = useCallback(
        ({ command, index }: { command: Command; index: number }) => (
            <motion.div
                key={command.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                    duration: 0.3,
                    delay: Math.min(0.03 * (index % ITEMS_PER_LOAD), 0.2),
                    ease: "easeOut"
                }}
                layoutId={`card-${command.name}`}>
                <CommandCard
                    command={command}
                    isSelected={selectedCommand?.name === command.name}
                    onClick={() =>
                        setSelectedCommand(selectedCommand?.name === command.name ? null : command)
                    }
                    onCopy={() => copyCommand(command.name)}
                />
            </motion.div>
        ),
        [selectedCommand, copyCommand]
    )

    return (
        <div className="relative w-full min-h-screen bg-[#0A0A0B] font-sans tracking-tight text-white">
            <Toaster position="bottom-center" />

            <main className="relative z-10">
                <div className=" pb-16">
                    <div className="relative border-b border-white/5 bg-black/20">
                        <div className="absolute inset-0 top-0 bg-[url('/noise.png')] opacity-5" />
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 pt-24 relative">
                            <div className="text-center">
                                <span className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 md:mb-6 bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block">
                                    Commands
                                </span>
                                <p className="text-base sm:text-lg text-gray-400 max-w-3xl mx-auto">
                                    Explore and learn about all available commands.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-8 mt-8">
                        <div className="flex flex-col md:flex-row md:items-center gap-4">
                            <div className="relative flex-grow">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Search className="h-5 w-5 text-evict-primary/40" />
                                </div>
                                <input
                                    type="text"
                                    placeholder="Search commands by name, description, or aliases..."
                                    className="w-full bg-evict-200 border border-evict-card-border rounded-full pl-10 pr-4 py-3 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
                                    value={searchQuery}
                                    onChange={e => setSearchQuery(e.target.value)}
                                />
                                {searchQuery && (
                                    <button
                                        onClick={() => setSearchQuery("")}
                                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-white/40 hover:text-white/80">
                                        <X className="h-5 w-5" />
                                    </button>
                                )}
                            </div>

                            <div className="relative" ref={filterRef}>
                                <button
                                    onClick={() => setShowFilters(!showFilters)}
                                    className="flex items-center justify-center gap-2 px-5 py-3 bg-white/5 backdrop-blur-lg border border-white/10 rounded-full text-white hover:bg-white/10 transition-all whitespace-nowrap">
                                    <Filter className="w-4 h-4 text-evict-primary/80" />
                                    <span>
                                        Filter by Category
                                        {activeCategory !== "All" ? `: ${activeCategory}` : ""}
                                    </span>
                                    {showFilters ? (
                                        <ChevronUp className="w-4 h-4" />
                                    ) : (
                                        <ChevronDown className="w-4 h-4" />
                                    )}
                                </button>

                                {showFilters && (
                                    <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-black/80 backdrop-blur-xl border border-white/10 shadow-lg z-50 p-2">
                                        <div className="grid grid-cols-1 gap-1.5 max-h-[50vh] overflow-y-auto p-2">
                                            {Categories.map(category => (
                                                <button
                                                    key={category.name}
                                                    onClick={() => {
                                                        setActiveCategory(category.name)
                                                        setShowFilters(false)
                                                    }}
                                                    className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all ${
                                                        activeCategory === category.name
                                                            ? "bg-white/10 text-white"
                                                            : "text-white/70 hover:bg-white/5"
                                                    }`}>
                                                    <div className="flex items-center gap-2">
                                                        <span
                                                            className={
                                                                activeCategory === category.name
                                                                    ? "text-evict-primary"
                                                                    : "text-evict-primary/40"
                                                            }>
                                                            {category.icon}
                                                        </span>
                                                        <span>{category.name}</span>
                                                    </div>

                                                    <span className="text-xs px-1.5 py-0.5 rounded-full bg-evict-primary/10 text-evict-primary/80 border border-evict-primary/20">
                                                        {getCategoryCount(category.name)}
                                                    </span>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-10">
                        {visibleCommands.length > 0 ? (
                            <>
                                <div className="mb-6 flex justify-between items-center">
                                    <h2 className="text-xl font-medium text-white">
                                        {activeCategory} Commands{" "}
                                        <span className="text-white/50">
                                            ({filteredCommands.length})
                                        </span>
                                    </h2>
                                    <div className="text-sm text-white/60">
                                        Showing {Math.min(visibleItems, filteredCommands.length)} of{" "}
                                        {filteredCommands.length}
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {visibleCommands.map((command, index) =>
                                        renderCommandCard({ command, index })
                                    )}
                                </div>

                                {visibleItems < filteredCommands.length && (
                                    <div className="flex justify-center mt-8">
                                        <button
                                            onClick={loadMore}
                                            className="px-8 py-3 bg-white/5 backdrop-blur-lg border border-white/10 rounded-full text-white hover:bg-white/10 transition-all">
                                            Load More Commands
                                        </button>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="flex flex-col items-center justify-center p-12 text-center bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl">
                                <div className="bg-white/5 p-4 rounded-full mb-4">
                                    <Search className="w-8 h-8 text-evict-primary/80" />
                                </div>
                                <h3 className="text-xl font-medium text-white">
                                    No commands found
                                </h3>
                                <p className="text-white/60 mt-2 max-w-md">
                                    Try adjusting your search query or selecting a different
                                    category filter
                                </p>
                                {(searchQuery || activeCategory !== "All") && (
                                    <button
                                        onClick={() => {
                                            setSearchQuery("")
                                            setActiveCategory("All")
                                        }}
                                        className="mt-6 px-6 py-2 bg-white/10 rounded-full text-white hover:bg-white/15 transition-all">
                                        Reset Filters
                                    </button>
                                )}
                            </div>
                        )}
                    </div>

                    <AnimatePresence>
                        {selectedCommand && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/80"
                                onClick={() => setSelectedCommand(null)}>
                                <motion.div
                                    layoutId={`card-${selectedCommand.name}`}
                                    className="w-full max-w-2xl bg-evict-200 border border-evict-card-border rounded-xl overflow-hidden"
                                    onClick={e => e.stopPropagation()}>
                                    <div className="p-6">
                                        <div className="flex items-center justify-between">
                                            <h2 className="text-2xl font-bold text-white">
                                                {selectedCommand.name}
                                            </h2>
                                            <button
                                                onClick={() => setSelectedCommand(null)}
                                                className="p-2 rounded-lg bg-evict-400 hover:bg-evict-300 transition-colors"
                                                title="Close"
                                                aria-label="Close">
                                                <X size={16} className="text-white/70" />
                                            </button>
                                        </div>

                                        <div className="mt-6 space-y-6">
                                            <div className="bg-evict-400 rounded-xl p-4">
                                                <h4 className="text-md font-medium text-white mb-3 flex items-center gap-2">
                                                    <span className="w-1 h-4 bg-white/20 rounded-sm"></span>
                                                    Usage
                                                </h4>
                                                <div className="bg-evict-300 rounded-lg p-4 font-mono text-white/70 border border-evict-card-border overflow-x-auto">
                                                    <code>
                                                        {selectedCommand.name}{" "}
                                                        {selectedCommand.parameters
                                                            .map((p, i) =>
                                                                p.optional
                                                                    ? `[${p.name}${p.flags?.required?.length ? ":flags" : ""}]`
                                                                    : `<${p.name}${p.flags?.required?.length ? ":flags" : ""}>`
                                                            )
                                                            .join(" ")}
                                                    </code>
                                                </div>
                                            </div>

                                            {selectedCommand.parameters.length > 0 && (
                                                <div className="bg-evict-400 rounded-xl p-4">
                                                    <h4 className="text-md font-medium text-white mb-3 flex items-center gap-2">
                                                        <span className="w-1 h-4 bg-white/20 rounded-sm"></span>
                                                        Parameters
                                                    </h4>
                                                    <div className="space-y-3">
                                                        {selectedCommand.parameters.map(
                                                            (param, idx) => (
                                                                <div
                                                                    key={idx}
                                                                    className="p-4 rounded-lg bg-evict-300 border border-evict-card-border">
                                                                    <div className="flex items-center justify-between mb-2">
                                                                        <div className="flex items-center gap-2">
                                                                            <span className="text-white font-medium">
                                                                                {param.name}
                                                                            </span>
                                                                            {param.optional && (
                                                                                <span className="px-2 py-0.5 rounded-full text-xs bg-white/10 text-white/70 border border-white/20">
                                                                                    Optional
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                        <span className="text-xs px-2 py-1 rounded-full bg-white/10 text-white/70">
                                                                            {param.type}
                                                                        </span>
                                                                    </div>

                                                                    {param.flags && (
                                                                        <div className="mt-3 pt-3 border-t border-white/10">
                                                                            <div className="text-sm text-white/70 mb-2">
                                                                                Flags:
                                                                            </div>
                                                                            <div className="flex flex-wrap gap-2">
                                                                                {param.flags.required?.map(
                                                                                    flag => (
                                                                                        <span
                                                                                            key={
                                                                                                flag.name
                                                                                            }
                                                                                            className="px-2 py-1 rounded-md text-xs bg-red-500/10 text-red-400 border border-red-500/20"
                                                                                            title={
                                                                                                flag.description
                                                                                            }>
                                                                                            {
                                                                                                flag.name
                                                                                            }
                                                                                        </span>
                                                                                    )
                                                                                )}
                                                                                {param.flags.optional?.map(
                                                                                    flag => (
                                                                                        <span
                                                                                            key={
                                                                                                flag.name
                                                                                            }
                                                                                            className="px-2 py-1 rounded-md text-xs bg-white/10 text-white/70 border border-white/10"
                                                                                            title={
                                                                                                flag.description
                                                                                            }>
                                                                                            {
                                                                                                flag.name
                                                                                            }
                                                                                        </span>
                                                                                    )
                                                                                )}
                                                                            </div>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            )
                                                        )}
                                                    </div>
                                                </div>
                                            )}

                                            {selectedCommand.permissions.length > 0 && (
                                                <div className="bg-evict-400 rounded-xl p-4">
                                                    <h4 className="text-md font-medium text-white mb-3 flex items-center gap-2">
                                                        <span className="w-1 h-4 bg-red-500/50 rounded-sm"></span>
                                                        Required Permissions
                                                    </h4>
                                                    <div className="flex flex-wrap gap-2">
                                                        {selectedCommand.permissions.map(
                                                            permission => (
                                                                <span
                                                                    key={permission}
                                                                    className="px-3 py-1.5 rounded-md text-sm bg-evict-300 text-white/70 border border-evict-card-border">
                                                                    {permission}
                                                                </span>
                                                            )
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </motion.div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    )
}

const CommandCard = React.memo(
    ({
        command,
        isSelected,
        onClick,
        onCopy
    }: {
        command: Command
        isSelected: boolean
        onClick: () => void
        onCopy: () => void
    }) => {
        const handleCopyClick = (e: React.MouseEvent) => {
            e.stopPropagation()
            onCopy()
        }

        return (
            <div
                onClick={onClick}
                className="relative h-full bg-evict-200 border border-evict-card-border hover:border-white/20 rounded-xl transition-all cursor-pointer">
                {command.donator && (
                    <div className="absolute top-2 right-2">
                        <span className="px-2 py-1 text-xs rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                            Donator
                        </span>
                    </div>
                )}

                <div className="p-5 h-full flex flex-col">
                    <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <h3 className="text-lg font-semibold text-white">{command.name}</h3>
                            <button
                                onClick={handleCopyClick}
                                className="p-1.5 rounded-md bg-white/5 hover:bg-white/15 transition-colors">
                                <Copy size={14} className="text-evict-primary/80" />
                            </button>
                        </div>

                        {command.donator && (
                            <span className="absolute top-1 right-1 text-xs text-amber-300">
                                Donator
                            </span>
                        )}
                    </div>

                    <p className="text-sm text-white/70 line-clamp-2 mb-3 flex-grow">
                        {command.description}
                    </p>

                    <div className="flex items-center justify-between mt-auto pt-2">
                        <div className="flex items-center gap-1">
                            <span className="px-2 py-0.5 text-xs rounded-full bg-evict-400 text-evict-primary/80 border border-evict-card-border">
                                {command.category}
                            </span>
                        </div>

                        <div className="text-sm text-white/50">
                            <div className="flex items-center gap-1">
                                <ExternalLink size={12} className="text-evict-primary/80" />
                                <span>Details</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        )
    }
)

CommandCard.displayName = "CommandCard"

export default CommandsPage
