"use client"
import { ChevronDown, Menu, X, Shield, Music, Wallet, Gift, Code, FileText, Bot } from "lucide-react"
import Image from "next/image"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import NavItem from "./NavItem"
import { motion } from "framer-motion"

const DiscordIcon = () => (
    <svg viewBox="0 -28.5 256 256" className="w-5 h-5" fill="currentColor">
        <path d="M216.856339,16.5966031 C200.285002,8.84328665 182.566144,3.2084988 164.041564,0 C161.766523,4.11318106 159.108624,9.64549908 157.276099,14.0464379 C137.583995,11.0849896 118.072967,11.0849896 98.7430163,14.0464379 C96.9108417,9.64549908 94.1925838,4.11318106 91.8971895,0 C73.3526068,3.2084988 55.6133949,8.86399117 39.0420583,16.6376612 C5.61752293,67.146514 -3.4433191,116.400813 1.08711069,164.955721 C23.2560196,181.510915 44.7403634,191.567697 65.8621325,198.148576 C71.0772151,190.971126 75.7283628,183.341335 79.7352139,175.300261 C72.104019,172.400575 64.7949724,168.822202 57.8887866,164.667963 C59.7209612,163.310589 61.5131304,161.891452 63.2445898,160.431257 C105.36741,180.133187 151.134928,180.133187 192.754523,160.431257 C194.506336,161.891452 196.298154,163.310589 198.110326,164.667963 C191.183787,168.842556 183.854737,172.420929 176.223542,175.320965 C180.230393,183.341335 184.861538,190.991831 190.096624,198.16893 C211.238746,191.588051 232.743023,181.531619 254.911949,164.955721 C260.227747,108.668201 245.831087,59.8662432 216.856339,16.5966031 Z M85.4738752,135.09489 C72.8290281,135.09489 62.4592217,123.290155 62.4592217,108.914901 C62.4592217,94.5396472 72.607595,82.7145587 85.4738752,82.7145587 C98.3405064,82.7145587 108.709962,94.5189427 108.488529,108.914901 C108.508531,123.290155 98.3405064,135.09489 85.4738752,135.09489 Z M170.525237,135.09489 C157.88039,135.09489 147.510584,123.290155 147.510584,108.914901 C147.510584,94.5396472 157.658606,82.7145587 170.525237,82.7145587 C183.391518,82.7145587 193.761324,94.5189427 193.539891,108.914901 C193.539891,123.290155 183.391518,135.09489 170.525237,135.09489 Z" />
    </svg>
)

interface NavbarProps {
    children?: React.ReactNode
}

export default function Navbar({ children }: NavbarProps) {
    const pathname = usePathname()
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
    const [isScrolled, setIsScrolled] = useState(false)
    const [scrollProgress, setScrollProgress] = useState(0)

    const [isOnline, setIsOnline] = useState<boolean>(true)
    const [isLoading, setIsLoading] = useState<boolean>(true)

    useEffect(() => {
        let timeoutId: NodeJS.Timeout
        let rafId: number

        const handleScroll = () => {
            rafId = requestAnimationFrame(() => {
                const scrollY = window.scrollY
                const threshold = 150

                const progress = Math.min(scrollY / threshold, 1)
                const easedProgress = progress * (2 - progress)
                setScrollProgress(easedProgress)

                clearTimeout(timeoutId)
                timeoutId = setTimeout(() => {
                    setIsScrolled(easedProgress > 0.3)
                }, 50)
            })
        }

        window.addEventListener("scroll", handleScroll, { passive: true })
        return () => {
            window.removeEventListener("scroll", handleScroll)
            clearTimeout(timeoutId)
            cancelAnimationFrame(rafId)
        }
    }, [])

    useEffect(() => {
        const apiKey = "a70c1ab9-2b72-4371-a3cb-a499f24f127f"

        const checkStatus = async () => {
            try {
                setIsLoading(true)
                const response = await fetch("https://api.evict.bot/status", {
                    cache: "no-store"
                })

                setIsOnline(response.ok)
                setIsLoading(false)
            } catch (error) {
                console.error("Failed to fetch status:", error)
                setIsOnline(false)
                setIsLoading(false)
            }
        }

        checkStatus()
        const interval = setInterval(checkStatus, 60000)

        return () => clearInterval(interval)
    }, [])

    const routes = useMemo(
        () => [
            {
                label: "Features",
                destination: "#",
                isActive: Boolean(pathname && pathname.startsWith("/features"))
            },
            {
                label: "Tools",
                destination: "#",
                isActive: Boolean(pathname && pathname.startsWith("/tools"))
            },
            {
                label: "Commands",
                destination: "/commands",
                isActive: pathname === "/commands"
            },
            {
                label: "Status",
                destination: "/status",
                isActive: pathname === "/status",
                statusIndicator: true
            }
        ],
        [pathname]
    )

    return (
        <>
            <div className="fixed top-0 left-0 right-0 z-50 mt-3 sm:mt-6 font-sans px-3 sm:px-0 pointer-events-none">
                <div
                    className={`w-full sm:w-fit mx-auto transform-gpu will-change-transform transition-all duration-1000 ease-[cubic-bezier(0.22,1,0.36,1)] pointer-events-auto ${
                        isScrolled ? "scale-[0.97]" : "scale-100"
                    }`}
                    style={{
                        transform: `scale(${1 - scrollProgress * 0.03})`,
                        transition: "all 1000ms cubic-bezier(0.22, 1, 0.36, 1)"
                    }}>
                    <div className="bg-[#0F0F0F]/90 backdrop-blur-md shadow-lg rounded-full py-2 px-3 sm:py-2.5 sm:px-5 transition-all duration-1000 ease-[cubic-bezier(0.22,1,0.36,1)]">
                        <div className="flex items-center justify-between sm:justify-start gap-2 sm:gap-3 transition-all duration-1000 ease-[cubic-bezier(0.22,1,0.36,1)]">
                            <Link href="/" className="flex-shrink-0">
                                <Image
                                    src="https://r2.evict.bot/evict-marketing.png"
                                    alt="Evict"
                                    width={26}
                                    height={26}
                                    className="rounded-full"
                                />
                            </Link>

                            <div className="hidden md:flex items-center gap-3">
                                <NavItem
                                    label="Features"
                                    destination="#"
                                    isActive={Boolean(pathname && pathname.startsWith("/features"))}
                                />

                                <NavItem
                                    label="Tools"
                                    destination="#"
                                    isActive={Boolean(pathname && pathname.startsWith("/tools"))}
                                />

                                <NavItem
                                    label="Commands"
                                    destination="/commands"
                                    isActive={pathname === "/commands"}
                                />

                                <div
                                    className={`flex items-center transform-gpu will-change-transform transition-all duration-1000 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                                        isScrolled
                                            ? "w-0 opacity-0 overflow-hidden"
                                            : "w-auto opacity-100"
                                    }`}
                                    style={{
                                        opacity: 1 - scrollProgress,
                                        width: scrollProgress > 0.3 ? "0px" : "auto",
                                        marginRight: scrollProgress > 0.3 ? "0px" : "12px",
                                        transform: `translateX(${scrollProgress > 0.3 ? "-20px" : "0px"})`,
                                        transition: "all 1000ms cubic-bezier(0.22, 1, 0.36, 1)"
                                    }}>
                                    <Link
                                        href="/status"
                                        className="text-sm font-medium text-gray-400 hover:text-white transition-colors whitespace-nowrap">
                                        Status
                                    </Link>
                                </div>

                                <div
                                    className={`w-2 h-2 rounded-full transition-all duration-500 ${
                                        isLoading
                                            ? "bg-gray-500"
                                            : isOnline
                                              ? "bg-evict-primary"
                                              : "bg-red-500"
                                    }`}
                                />

                                <Link
                                    href="/invite"
                                    className={`relative transform-gpu will-change-transform transition-all duration-1000 ease-[cubic-bezier(0.22,1,0.36,1)] bg-evict-primary text-evict-100 hover:bg-opacity-90 rounded-full font-medium text-sm flex items-center justify-center overflow-hidden ${
                                        isScrolled ? "w-9 h-9" : "w-[140px] h-9"
                                    }`}
                                    style={{
                                        width: scrollProgress > 0.3 ? "36px" : "140px",
                                        height: "36px",
                                        transition: "all 1000ms cubic-bezier(0.22, 1, 0.36, 1)"
                                    }}>
                                    <div
                                        className="absolute inset-0 flex items-center justify-center"
                                        style={{
                                            opacity: scrollProgress > 0.3 ? 1 : 0,
                                            transform: `translateY(${scrollProgress > 0.3 ? "0%" : "100%"}) scale(${scrollProgress > 0.3 ? "1" : "0.5"})`,
                                            transition: "all 1000ms cubic-bezier(0.22, 1, 0.36, 1)",
                                            transitionDelay: scrollProgress > 0.3 ? "0ms" : "200ms"
                                        }}>
                                        <DiscordIcon />
                                    </div>
                                    <div
                                        className="absolute inset-0 flex items-center justify-center whitespace-nowrap"
                                        style={{
                                            opacity: scrollProgress > 0.3 ? 0 : 1,
                                            transform: `translateY(${scrollProgress > 0.3 ? "-20%" : "0%"}) scale(${scrollProgress > 0.3 ? "0.9" : "1"})`,
                                            transition: "all 1000ms cubic-bezier(0.22, 1, 0.36, 1)",
                                            transitionDelay: scrollProgress > 0.3 ? "0ms" : "100ms"
                                        }}>
                                        <span>Add to Discord</span>
                                    </div>
                                </Link>
                            </div>

                            <div className="flex items-center gap-2 sm:gap-3 md:hidden">
                                <Link
                                    href="/invite"
                                    className="bg-evict-primary hover:bg-opacity-90 text-evict-100 rounded-full font-medium text-sm flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 transition-all">
                                    <DiscordIcon />
                                </Link>

                                <button
                                    className="p-1.5 sm:p-2 text-gray-400 hover:text-white transition-colors bg-white/5 rounded-full"
                                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
                                    {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
                                </button>
                            </div>
                        </div>

                        {isMobileMenuOpen && (
                            <div className="md:hidden fixed inset-x-0 top-[4.5rem] sm:top-20 p-3 sm:px-6">
                                <motion.div
                                    initial={{ opacity: 0, y: -20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="bg-[#0F0F0F]/90 backdrop-blur-md rounded-3xl shadow-lg border border-white/[0.05] overflow-hidden">
                                    <div className="flex flex-col divide-y divide-white/[0.05]">
                                        {/* Features Section */}
                                        <div className="p-4">
                                            <div className="flex items-center justify-between text-[0.95rem] font-medium text-white mb-4">
                                                <span>Features</span>
                                            </div>
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                                <Link
                                                    href="/features/moderation"
                                                    className="group flex items-start gap-3 p-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200"
                                                    onClick={() => setIsMobileMenuOpen(false)}>
                                                    <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                        <Shield className="w-5 h-5 text-evict-primary/80" />
                                                    </div>
                                                    <div>
                                                        <div className="font-medium text-white mb-1">Moderation</div>
                                                        <p className="text-xs text-zinc-400">Advanced auto-moderation system</p>
                                                    </div>
                                                </Link>

                                                <Link
                                                    href="/features/voice"
                                                    className="group flex items-start gap-3 p-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200"
                                                    onClick={() => setIsMobileMenuOpen(false)}>
                                                    <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                        <Music className="w-5 h-5 text-evict-primary/80" />
                                                    </div>
                                                    <div>
                                                        <div className="font-medium text-white mb-1">Music Player</div>
                                                        <p className="text-xs text-zinc-400">High quality music playback</p>
                                                    </div>
                                                </Link>

                                                <Link
                                                    href="/features/economy"
                                                    className="group flex items-start gap-3 p-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200"
                                                    onClick={() => setIsMobileMenuOpen(false)}>
                                                    <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                        <Wallet className="w-5 h-5 text-evict-primary/80" />
                                                    </div>
                                                    <div>
                                                        <div className="font-medium text-white mb-1">Economy</div>
                                                        <p className="text-xs text-zinc-400">Complete economy system</p>
                                                    </div>
                                                </Link>

                                                <Link
                                                    href="/features/giveaway"
                                                    className="group flex items-start gap-3 p-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200"
                                                    onClick={() => setIsMobileMenuOpen(false)}>
                                                    <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                        <Gift className="w-5 h-5 text-evict-primary/80" />
                                                    </div>
                                                    <div>
                                                        <div className="font-medium text-white mb-1">Giveaways</div>
                                                        <p className="text-xs text-zinc-400">Easy to use giveaway system</p>
                                                    </div>
                                                </Link>

                                                <Link
                                                    href="/features/welcome"
                                                    className="group flex items-start gap-3 p-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200"
                                                    onClick={() => setIsMobileMenuOpen(false)}>
                                                    <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                        <Bot className="w-5 h-5 text-evict-primary/80" />
                                                    </div>
                                                    <div>
                                                        <div className="font-medium text-white mb-1">Welcome</div>
                                                        <p className="text-xs text-zinc-400">Customizable welcome messages</p>
                                                    </div>
                                                </Link>
                                            </div>
                                        </div>

                                        {/* Tools Section */}
                                        <div className="p-4">
                                            <div className="flex items-center justify-between text-[0.95rem] font-medium text-white mb-4">
                                                <span>Tools</span>
                                            </div>
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                                <Link
                                                    href="/embed"
                                                    className="group flex items-start gap-3 p-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200"
                                                    onClick={() => setIsMobileMenuOpen(false)}>
                                                    <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                        <Code className="w-5 h-5 text-evict-primary/80" />
                                                    </div>
                                                    <div>
                                                        <div className="font-medium text-white mb-1">Embed Builder</div>
                                                        <p className="text-xs text-zinc-400">Create beautiful embeds</p>
                                                    </div>
                                                </Link>

                                                <a
                                                    href="https://docs.evict.bot"
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="group flex items-start gap-3 p-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] transition-all duration-200"
                                                    onClick={() => setIsMobileMenuOpen(false)}>
                                                    <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                        <FileText className="w-5 h-5 text-evict-primary/80" />
                                                    </div>
                                                    <div>
                                                        <div className="font-medium text-white mb-1">Documentation</div>
                                                        <p className="text-xs text-zinc-400">Learn how to use Evict</p>
                                                    </div>
                                                </a>
                                            </div>
                                        </div>

                                        {/* Quick Links */}
                                        <div className="p-4">
                                            <div className="flex flex-col sm:flex-row gap-3">
                                                <Link
                                                    href="/commands"
                                                    className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] text-white font-medium transition-all duration-200"
                                                    onClick={() => setIsMobileMenuOpen(false)}>
                                                    Commands
                                                </Link>
                                                <Link
                                                    href="/status"
                                                    className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] text-white font-medium transition-all duration-200"
                                                    onClick={() => setIsMobileMenuOpen(false)}>
                                                    <span>Status</span>
                                                    <div className={`w-2 h-2 rounded-full transition-all duration-500 ${
                                                        isLoading
                                                            ? "bg-gray-500"
                                                            : isOnline
                                                            ? "bg-evict-primary"
                                                            : "bg-red-500"
                                                    }`} />
                                                </Link>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
            {children}
        </>
    )
}
