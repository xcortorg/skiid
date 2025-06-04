"use client"
import { motion } from "framer-motion"
import { Bot, ChevronDown, Gift, Music, Shield, Wallet, FileText, Code } from "lucide-react"
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
                <button className="font-medium text-[#71767C] hover:text-[#8B8F95] flex items-center gap-1">
                    {label}
                    <ChevronDown className="w-4 h-4" />
                </button>

                {showDropdown && (
                    <div className="absolute top-full left-0 pt-4 z-50">
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="w-[800px] bg-[#0A0A0B] border border-zinc-800/50 rounded-xl shadow-xl overflow-hidden">
                            <div className="p-4 grid grid-cols-[300px,1fr] gap-4">
                                <Link
                                    href="/features/moderation"
                                    className="flex flex-col justify-between h-full p-4 rounded-lg hover:bg-white/[0.02] transition-colors">
                                    <div>
                                        <div className="flex items-center gap-3 mb-2">
                                            <Shield className="w-5 h-5 text-blue-400" />
                                            <div className="font-medium text-white">Moderation</div>
                                        </div>
                                        <p className="text-sm text-zinc-400">
                                            Advanced auto-moderation system with customizable
                                            filters, anti-spam, and content detection
                                        </p>
                                    </div>
                                    <div className="text-sm text-zinc-400 mt-4">
                                        Protect your server with advanced filters and automated
                                        actions
                                    </div>
                                </Link>

                                <div className="grid grid-cols-2 gap-4">
                                    <Link
                                        href="/features/voice"
                                        className="p-4 rounded-lg hover:bg-white/[0.02] transition-colors">
                                        <div className="flex items-center gap-3 mb-1">
                                            <Music className="w-5 h-5 text-purple-400" />
                                            <div className="font-medium text-white">
                                                Music Player
                                            </div>
                                        </div>
                                        <p className="text-sm text-zinc-400">
                                            High quality music with playlist support
                                        </p>
                                    </Link>

                                    <Link
                                        href="/features/economy"
                                        className="p-4 rounded-lg hover:bg-white/[0.02] transition-colors">
                                        <div className="flex items-center gap-3 mb-1">
                                            <Wallet className="w-5 h-5 text-green-400" />
                                            <div className="font-medium text-white">Economy</div>
                                        </div>
                                        <p className="text-sm text-zinc-400">
                                            Complete economy system with businesses
                                        </p>
                                    </Link>

                                    <Link
                                        href="/features/giveaway"
                                        className="p-4 rounded-lg hover:bg-white/[0.02] transition-colors">
                                        <div className="flex items-center gap-3 mb-1">
                                            <Gift className="w-5 h-5 text-yellow-400" />
                                            <div className="font-medium text-white">Giveaways</div>
                                        </div>
                                        <p className="text-sm text-zinc-400">
                                            Easy to use giveaway system
                                        </p>
                                    </Link>

                                    <Link
                                        href="/features/welcome"
                                        className="p-4 rounded-lg hover:bg-white/[0.02] transition-colors">
                                        <div className="flex items-center gap-3 mb-1">
                                            <Bot className="w-5 h-5 text-red-400" />
                                            <div className="font-medium text-white">Welcome</div>
                                        </div>
                                        <p className="text-sm text-zinc-400">
                                            Customizable welcome messages
                                        </p>
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
                <button className="font-medium text-[#71767C] hover:text-[#8B8F95] flex items-center gap-1">
                    {label}
                    <ChevronDown className="w-4 h-4" />
                </button>

                {showDropdown && (
                    <div className="absolute top-full left-0 pt-4 z-50">
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="w-[400px] bg-[#0A0A0B] border border-zinc-800/50 rounded-xl shadow-xl overflow-hidden">
                            <div className="p-4 space-y-2">
                                <Link
                                    href="/embed"
                                    className="flex items-center gap-3 p-4 rounded-lg hover:bg-white/[0.02] transition-colors">
                                    <Code className="w-5 h-5 text-blue-400" />
                                    <div>
                                        <div className="font-medium text-white">Embed Builder</div>
                                        <p className="text-sm text-zinc-400">Create beautiful embeds for your server</p>
                                    </div>
                                </Link>

                                <a
                                    href="https://docs.evict.bot"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-3 p-4 rounded-lg hover:bg-white/[0.02] transition-colors">
                                    <FileText className="w-5 h-5 text-purple-400" />
                                    <div>
                                        <div className="font-medium text-white">Documentation</div>
                                        <p className="text-sm text-zinc-400">Learn how to use Evict</p>
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
