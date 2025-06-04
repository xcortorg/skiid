"use client"
import { motion } from "framer-motion"
import { Bot, ChevronDown, Code, FileText, Gift, Music, Shield, Wallet } from "lucide-react"
import Link from "next/link"
import { useCallback, useRef, useState } from "react"

interface NavItemProps {
    label: string
    destination: string
    isActive: boolean
}

const NavItem: React.FC<NavItemProps> = ({ label, destination, isActive }) => {
    const [showDropdown, setShowDropdown] = useState(false)
    const timeoutRef = useRef<NodeJS.Timeout | null>(null)

    const clearTimeoutRef = () => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current)
            timeoutRef.current = null
        }
    }

    const handleMouseEnter = useCallback(() => {
        clearTimeoutRef()
        setShowDropdown(true)
    }, [])

    const handleMouseLeave = useCallback(() => {
        timeoutRef.current = setTimeout(() => {
            setShowDropdown(false)
        }, 150)
    }, [])

    if (label === "Features") {
        return (
            <div
                className="relative"
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}>
                <button className={`font-medium flex items-center gap-1 transition-colors ${isActive ? "text-evict-primary" : "text-[#71767C] hover:text-[#8B8F95]"}`}>
                    {label}
                    <motion.div
                        animate={{ rotate: showDropdown ? 180 : 0 }}
                        transition={{ duration: 0.2 }}>
                        <ChevronDown className="w-4 h-4" />
                    </motion.div>
                </button>

                {showDropdown && (
                    <div className="absolute top-full left-0 pt-3 z-50">
                        <motion.div
                            initial={{ opacity: 0, y: 10, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            transition={{
                                duration: 0.2,
                                ease: [0.4, 0, 0.2, 1]
                            }}
                            className="w-[700px] bg-[#0A0A0B] border border-white/[0.05] rounded-2xl shadow-xl overflow-hidden">
                            <div className="p-4 grid grid-cols-[240px,1fr] gap-4">
                                <Link
                                    href="/features/moderation"
                                    className="group flex flex-col justify-between h-full p-4 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200">
                                    <div>
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                <Shield className="w-5 h-5 text-evict-primary/80" />
                                            </div>
                                            <div className="font-medium text-white">Moderation</div>
                                        </div>
                                        <p className="text-sm text-zinc-400 leading-relaxed">
                                            Advanced auto-moderation system with customizable
                                            filters and anti-spam
                                        </p>
                                    </div>
                                    <div className="text-xs text-zinc-500 mt-3 group-hover:text-evict-primary/60 transition-colors">
                                        Protect your server with advanced filters →
                                    </div>
                                </Link>

                                <div className="grid grid-cols-2 gap-3">
                                    <Link
                                        href="/features/voice"
                                        className="group p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200">
                                        <div className="flex items-center gap-3 mb-1.5">
                                            <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                <Music className="w-5 h-5 text-evict-primary/80" />
                                            </div>
                                            <div className="font-medium text-white">
                                                Music Player
                                            </div>
                                        </div>
                                        <p className="text-sm text-zinc-400 mb-1.5">
                                            High quality music with playlist support
                                        </p>
                                        <div className="text-xs text-zinc-500 group-hover:text-evict-primary/60 transition-colors">
                                            Learn more →
                                        </div>
                                    </Link>

                                    <Link
                                        href="/features/economy"
                                        className="group p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200">
                                        <div className="flex items-center gap-3 mb-1.5">
                                            <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                <Wallet className="w-5 h-5 text-evict-primary/80" />
                                            </div>
                                            <div className="font-medium text-white">Economy</div>
                                        </div>
                                        <p className="text-sm text-zinc-400 mb-1.5">
                                            Complete economy system with businesses
                                        </p>
                                        <div className="text-xs text-zinc-500 group-hover:text-evict-primary/60 transition-colors">
                                            Learn more →
                                        </div>
                                    </Link>

                                    <Link
                                        href="/features/giveaway"
                                        className="group p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200">
                                        <div className="flex items-center gap-3 mb-1.5">
                                            <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                <Gift className="w-5 h-5 text-evict-primary/80" />
                                            </div>
                                            <div className="font-medium text-white">Giveaways</div>
                                        </div>
                                        <p className="text-sm text-zinc-400 mb-1.5">
                                            Easy to use giveaway system
                                        </p>
                                        <div className="text-xs text-zinc-500 group-hover:text-evict-primary/60 transition-colors">
                                            Learn more →
                                        </div>
                                    </Link>

                                    <Link
                                        href="/features/welcome"
                                        className="group p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200">
                                        <div className="flex items-center gap-3 mb-1.5">
                                            <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                <Bot className="w-5 h-5 text-evict-primary/80" />
                                            </div>
                                            <div className="font-medium text-white">Welcome</div>
                                        </div>
                                        <p className="text-sm text-zinc-400 mb-1.5">
                                            Customizable welcome messages
                                        </p>
                                        <div className="text-xs text-zinc-500 group-hover:text-evict-primary/60 transition-colors">
                                            Learn more →
                                        </div>
                                    </Link>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </div>
        )
    }

    if (label === "Tools") {
        return (
            <div
                className="relative"
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}>
                <button className={`font-medium flex items-center gap-1 transition-colors ${isActive ? "text-evict-primary" : "text-[#71767C] hover:text-[#8B8F95]"}`}>
                    {label}
                    <motion.div
                        animate={{ rotate: showDropdown ? 180 : 0 }}
                        transition={{ duration: 0.2 }}>
                        <ChevronDown className="w-4 h-4" />
                    </motion.div>
                </button>

                {showDropdown && (
                    <div className="absolute top-full left-0 pt-3 z-50">
                        <motion.div
                            initial={{ opacity: 0, y: 10, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            transition={{
                                duration: 0.2,
                                ease: [0.4, 0, 0.2, 1]
                            }}
                            className="w-[400px] bg-[#0A0A0B] border border-white/[0.05] rounded-2xl shadow-xl overflow-hidden">
                            <div className="p-4 space-y-2">
                                <Link
                                    href="/embed"
                                    className="group flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200">
                                    <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                        <Code className="w-5 h-5 text-evict-primary/80" />
                                    </div>
                                    <div>
                                        <div className="font-medium text-white mb-1">Embed Builder</div>
                                        <p className="text-sm text-zinc-400">
                                            Create beautiful embeds for your server
                                        </p>
                                    </div>
                                </Link>

                                <a
                                    href="https://docs.evict.bot"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="group flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200">
                                    <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                        <FileText className="w-5 h-5 text-evict-primary/80" />
                                    </div>
                                    <div>
                                        <div className="font-medium text-white mb-1">Documentation</div>
                                        <p className="text-sm text-zinc-400">
                                            Learn how to use Evict
                                        </p>
                                    </div>
                                </a>
                            </div>
                        </motion.div>
                    </div>
                )}
            </div>
        )
    }

    return (
        <Link href={destination} className={`font-medium text-[#71767C] hover:text-[#8B8F95]`}>
            {label}
        </Link>
    )
}

export default NavItem
