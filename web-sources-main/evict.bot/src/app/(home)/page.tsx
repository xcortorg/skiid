"use client"

import { AnimatePresence, motion } from "framer-motion"
import {
    Clock,
    Command,
    Crown,
    Gamepad2,
    Gift,
    HeartHandshake,
    MessageSquare,
    Music,
    Repeat,
    Settings,
    Shield,
    Shuffle,
    Sparkles,
    Star,
    Trophy,
    Users
} from "lucide-react"
import Image from "next/image"
import Link from "next/link"
import { useEffect, useState } from "react"
import CountUp from "react-countup"
import {
    FaBackward,
    FaForward,
    FaLastfm,
    FaPause,
    FaPlay,
    FaServer,
    FaSpotify,
    FaUsers,
    FaYoutube
} from "react-icons/fa"
import {
    HiChartBar,
    HiLockClosed,
    HiOutlineShieldCheck,
    HiOutlineStatusOnline
} from "react-icons/hi"
import { IoSettingsOutline, IoTerminal } from "react-icons/io5"
import { RiExternalLinkLine } from "react-icons/ri"
import { SiSpotify } from "react-icons/si"
import { useInView } from "react-intersection-observer"
import { Bar, BarChart, ResponsiveContainer, XAxis } from "recharts"

let cachedStats: any = null
let lastFetchTime: number | null = null
const CACHE_DURATION = 5 * 60 * 1000

function Counter({ from, to, duration }: { from: number; to: number; duration: number }) {
    const { ref, inView } = useInView({
        threshold: 0.2,
        triggerOnce: true
    })

    return (
        <span ref={ref} className="inline-block">
            {inView ? (
                <CountUp
                    start={from}
                    end={to}
                    separator=","
                    duration={2}
                    className="text-white font-semibold"
                />
            ) : (
                from.toLocaleString()
            )}
        </span>
    )
}

const container = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.15,
            delayChildren: 0.4,
            type: "spring",
            stiffness: 50,
            damping: 20
        }
    }
}

const item = {
    hidden: {
        opacity: 0,
        y: 8,
        filter: "blur(2px)"
    },
    show: {
        opacity: 1,
        y: 0,
        filter: "blur(0px)",
        transition: {
            type: "tween",
            ease: "easeOut",
            duration: 1.2,
            opacity: {
                duration: 0.8
            },
            filter: {
                duration: 1
            }
        }
    }
}

const HomePage = () => {
    const [stats, setStats] = useState({ users: 0, guilds: 0 })

    useEffect(() => {
        const fetchStats = async () => {
            try {
                if (cachedStats && lastFetchTime && Date.now() - lastFetchTime < CACHE_DURATION) {
                    setStats(cachedStats)
                    return
                }

                const response = await fetch("https://api.evict.bot/status")
                if (!response.ok) throw new Error(`API returned ${response.status}`)

                const data = await response.json()
                cachedStats = {
                    users: data.total.users,
                    guilds: data.total.guilds
                }
                lastFetchTime = Date.now()
                setStats(cachedStats)
            } catch (error) {
                console.error("Failed to fetch stats:", error)
            }
        }
        fetchStats()
    }, [])

    return (
        <AnimatePresence mode="wait">
            <motion.div
                key="homepage"
                className="relative w-full overflow-x-hidden mt-16"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6 }}>
                <motion.div
                    variants={container}
                    initial="hidden"
                    animate="show"
                    className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <motion.div
                        className="fixed inset-0 z-0 pointer-events-none opacity-[0.015] bg-noise"
                        variants={item}
                    />
                    <motion.div
                        className="fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-white/5 via-transparent to-zinc-400/5 mix-blend-overlay"
                        variants={item}
                    />

                    <div className="">
                        <motion.div
                            variants={item}
                            className="relative flex items-center justify-center min-h-[calc(100vh-4rem)]">
                            <motion.div
                                variants={container}
                                className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
                                <motion.div variants={item}>
                                    <Image
                                        src="https://r2.evict.bot/evict-new.png"
                                        alt="Evict"
                                        width={180}
                                        height={180}
                                        className="mx-auto mb-6 md:mb-8 drop-shadow-2xl rounded-3xl brightness-100 [filter:_brightness(1)_sepia(0.1)_saturate(1.65)_hue-rotate(220deg)]"
                                        priority
                                    />
                                </motion.div>
                                <h1 className="select-none text-5xl md:text-7xl font-bold leading-tight px-4">
                                    <motion.span
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{
                                            duration: 0.3,
                                            ease: [0.25, 0.1, 0, 1],
                                            delay: 0.2
                                        }}
                                        className="block bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                        The Ultimate
                                    </motion.span>
                                    <motion.span
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{
                                            duration: 0.3,
                                            ease: [0.25, 0.1, 0, 1],
                                            delay: 0.3
                                        }}
                                        className="block bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                        Discord Experience
                                    </motion.span>
                                </h1>
                                <motion.p
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{
                                        duration: 0.3,
                                        ease: [0.25, 0.1, 0, 1],
                                        delay: 0.4
                                    }}
                                    className="select-none mt-6 md:mt-8 text-lg md:text-xl max-w-2xl mx-auto px-4 leading-relaxed text-transparent bg-clip-text bg-gradient-to-r from-white to-evict-primary">
                                    Powering{" "}
                                    <motion.span
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{
                                            duration: 0.3,
                                            delay: 0.5
                                        }}
                                        className="from-white to-evict-primary bg-clip-text text-transparent">
                                        {stats.guilds.toLocaleString()}
                                    </motion.span>{" "}
                                    servers and serving{" "}
                                    <motion.span
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{
                                            duration: 0.3,
                                            delay: 0.6
                                        }}
                                        className="from-white to-evict-primary bg-clip-text text-transparent">
                                        {stats.users.toLocaleString()}
                                    </motion.span>{" "}
                                    users with advanced moderation, music, and utility features.
                                </motion.p>
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{
                                        duration: 0.3,
                                        ease: [0.25, 0.1, 0, 1],
                                        delay: 0.7
                                    }}
                                    className="mt-8 md:mt-10 flex flex-col sm:flex-row justify-center gap-3 px-4">
                                    <motion.div
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        transition={{ duration: 0.2 }}>
                                        <Link
                                            href="/invite"
                                            className="px-6 py-3 bg-evict-primary text-evict-100 rounded-xl font-medium hover:bg-opacity-90 transition-all flex items-center justify-center gap-2">
                                            Add to Discord
                                            <RiExternalLinkLine className="w-4 h-4" />
                                        </Link>
                                    </motion.div>
                                    <motion.div
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        transition={{ duration: 0.2 }}>
                                        <Link
                                            href="/commands"
                                            className="px-6 py-3 bg-evict-200/50 text-evict-primary rounded-xl font-medium hover:bg-evict-200/70 transition-all border border-evict-primary/20 flex items-center justify-center gap-2">
                                            <IoTerminal className="w-4 h-4" />
                                            View Commands
                                        </Link>
                                    </motion.div>
                                </motion.div>
                            </motion.div>
                        </motion.div>
                    </div>
                </motion.div>

                <div className="relative py-24 -mx-[calc((100vw-100%)/2)] bg-[#0A0A0B]">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="mb-16">
                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                className="space-y-3">
                                <span className="text-4xl font-medium bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block mb-4">
                                    Powerful protection, seamless experience
                                </span>
                                <p className="text-lg text-white/60 max-w-3xl">
                                    Advanced moderation meets intuitive design. From real-time raid
                                    protection to smart commands, Evict combines enterprise-grade
                                    security with a delightful user experience that keeps your
                                    community safe and engaged.
                                </p>
                            </motion.div>
                        </div>

                        <div className="select-none grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 auto-rows-[180px] gap-4 max-w-full">
                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                className="col-span-1 sm:col-span-2 row-span-3 group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-4 sm:p-6 hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="flex flex-col h-full">
                                    <div className="flex items-center justify-between mb-6">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 rounded-xl bg-white/5 border border-evict-primary/20">
                                                <HiOutlineShieldCheck className="w-6 h-6 text-evict-primary/80" />
                                            </div>
                                            <span className="text-sm font-medium text-evict-primary/80">
                                                Advanced Protection
                                            </span>
                                        </div>
                                        <span className="flex items-center gap-1 text-xs px-2 py-1 bg-black/20 rounded-full text-evict-primary/30">
                                            <HiLockClosed className="w-3 h-3" />
                                            <span>Enterprise-grade</span>
                                        </span>
                                    </div>

                                    <span className="text-3xl font-semibold bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent mb-4 block">
                                        Intelligent Moderation
                                    </span>

                                    <div className="grid grid-cols-2 gap-4 mb-6">
                                        {[
                                            {
                                                value: "99.9%",
                                                label: "Accuracy",
                                                trend: "+0.2%"
                                            },
                                            {
                                                value: "24/7",
                                                label: "Monitoring",
                                                trend: "Active"
                                            },
                                            {
                                                value: "<0.1%",
                                                label: "False Positives",
                                                trend: "-0.05%"
                                            },
                                            {
                                                value: "Real-time",
                                                label: "Response",
                                                trend: "<50ms"
                                            }
                                        ].map((stat, i) => (
                                            <div
                                                key={i}
                                                className="bg-black/20 rounded-xl p-4 hover:bg-black/30 transition-colors">
                                                <div className="text-2xl font-bold bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">
                                                    {stat.value}
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span className="text-sm text-white/40">
                                                        {stat.label}
                                                    </span>
                                                    <span className="text-xs text-white/30">
                                                        {stat.trend}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="flex-1 grid grid-cols-2 gap-3">
                                        {[
                                            { name: "Auto-moderation", count: "1.2M+" },
                                            { name: "Warning system", count: "50K+" },
                                            { name: "Anti-raid", count: "99.9%" },
                                            { name: "Logging", count: "Real-time" },
                                            { name: "Spam detection", count: "0.1s" },
                                            { name: "Content filter", count: "Smart" }
                                        ].map((feature, i) => (
                                            <div
                                                key={i}
                                                className="flex items-center justify-between bg-black/20 rounded-lg px-4 py-3 hover:bg-black/30 transition-colors">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-evict-primary/20" />
                                                    <span className="text-sm text-white/70">
                                                        {feature.name}
                                                    </span>
                                                </div>
                                                <span className="text-xs text-white/40">
                                                    {feature.count}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>

                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                className="col-span-1 sm:col-span-2 row-span-1 group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-4 sm:p-6 hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="flex flex-col h-full">
                                    <div className="flex items-center gap-4 mb-3">
                                        <div className="relative w-12 h-12 rounded-xl overflow-hidden">
                                            <Image
                                                src="/kendrick.jpg"
                                                alt="Album"
                                                fill
                                                className="object-cover"
                                            />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <FaSpotify className="w-3 h-3 text-evict-primary/60" />
                                                <span className="text-xs text-white/60">
                                                    Now Playing
                                                </span>
                                            </div>
                                            <h4 className="text-sm font-medium text-white mt-0.5 truncate">
                                                luther (with sza)
                                            </h4>
                                            <p className="text-xs text-white/40">
                                                Kendrick Lamar, SZA
                                            </p>
                                        </div>
                                        <button className="p-2 rounded-full bg-white/5 hover:bg-white/10 transition-colors">
                                            <FaPlay className="w-3 h-3 text-evict-primary/40" />
                                        </button>
                                    </div>

                                    <div className="flex items-center gap-2 mb-4">
                                        <span className="text-[10px] text-white/40">1:30</span>
                                        <div className="flex-1 h-0.5 bg-white/5 rounded-full overflow-hidden">
                                            <div className="w-1/3 h-full bg-evict-primary/40 rounded-full" />
                                        </div>
                                        <span className="text-[10px] text-white/40">4:26</span>
                                    </div>

                                    <div className="flex items-center gap-2 mb-2">
                                        <span className="text-xs text-evict-primary/40">
                                            Next up
                                        </span>
                                        <span className="text-[10px] text-white/20 -mt-0.5">•</span>
                                        <span className="text-xs text-evict-primary/20">
                                            3 tracks
                                        </span>
                                    </div>

                                    <div className="flex flex-wrap gap-1.5">
                                        {[
                                            {
                                                title: "I Wanna Be Yours",
                                                artist: "Arctic Monkeys",
                                                img: "/spotify/arctic.jpg"
                                            },
                                            {
                                                title: "To Ashes and Blood",
                                                artist: "Arcane, League of Legends",
                                                img: "/toashes.jpg"
                                            },
                                            {
                                                title: "VOID",
                                                artist: "Melanie Martinez",
                                                img: "/void.jpg"
                                            }
                                        ].map((track, i) => (
                                            <div
                                                key={i}
                                                className={`inline-flex items-center gap-1.5 bg-black/10 rounded-lg py-1 pl-1 pr-2 border border-white/5 hover:bg-black/20 transition-colors cursor-pointer group
                                                              ${i > 0 ? "hidden sm:inline-flex" : ""}`}>
                                                <div className="relative w-4 h-4 rounded-full overflow-hidden flex-shrink-0">
                                                    <Image
                                                        src={track.img}
                                                        alt={track.title}
                                                        fill
                                                        className="object-cover"
                                                    />
                                                </div>
                                                <div className="flex items-center gap-1 min-w-0">
                                                    <span className="text-[10px] text-white/70 truncate max-w-[80px] group-hover:text-white/90">
                                                        {track.title}
                                                    </span>
                                                    <span className="text-evict-primary/20 text-[10px]">
                                                        •
                                                    </span>
                                                    <span className="text-[10px] text-white/40 truncate max-w-[60px] group-hover:text-white/60">
                                                        {track.artist.split(",")[0]}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                        <div className="sm:hidden inline-flex items-center text-[10px] text-white/40">
                                            +2 more
                                        </div>
                                    </div>
                                </div>
                            </motion.div>

                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                className="col-span-1 row-span-1 group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-4 hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="flex flex-col h-full">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <div className="p-1.5 rounded-lg bg-white/5 border border-evict-primary/20">
                                                <Shield className="w-3.5 h-3.5 text-evict-primary/80" />
                                            </div>
                                            <span className="text-xs font-medium text-evict-primary/80">
                                                24h Overview
                                            </span>
                                        </div>
                                        <div className="flex -space-x-1.5">
                                            {["/adam-dc.png", "/bhop.png", "/fiji.png"].map(
                                                (avatar, i) => (
                                                    <div
                                                        key={i}
                                                        className="relative w-4 h-4 rounded-full overflow-hidden border border-evict-primary/20">
                                                        <Image
                                                            src={`/avs${avatar}`}
                                                            alt="Moderator"
                                                            fill
                                                            className="object-cover"
                                                        />
                                                    </div>
                                                )
                                            )}
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-1.5">
                                        {[
                                            { label: "Warnings", value: "12", color: "yellow" },
                                            { label: "Mutes", value: "8", color: "orange" },
                                            { label: "Kicks", value: "3", color: "red" },
                                            { label: "Bans", value: "1", color: "purple" }
                                        ].map((stat, i) => (
                                            <div
                                                key={i}
                                                className="bg-black/20 rounded-lg p-1.5 flex flex-col">
                                                <span className="text-[10px] text-white/40">
                                                    {stat.label}
                                                </span>
                                                <span className="text-sm font-semibold text-white/80">
                                                    {stat.value}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>

                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                className="col-span-1 row-span-1 group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-4 hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="h-full flex flex-col">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <div className="p-1.5 rounded-lg bg-white/5 border border-evict-primary/20">
                                                <IoSettingsOutline className="w-4 h-4 text-evict-primary/80" />
                                            </div>
                                            <span className="text-xs font-medium text-evict-primary/80">
                                                Activity
                                            </span>
                                        </div>
                                        <span className="flex items-center gap-1 text-xs px-2 py-1 bg-black/20 rounded-full text-evict-primary/30">
                                            <HiChartBar className="w-3 h-3" />
                                            <span>Last 7 days</span>
                                        </span>
                                    </div>

                                    <div className="flex-1 mt-6">
                                        <ResponsiveContainer width="100%" height={100}>
                                            <BarChart
                                                data={[
                                                    { day: "M", value: 42 },
                                                    { day: "T", value: 63 },
                                                    { day: "W", value: 45 },
                                                    { day: "T", value: 78 },
                                                    { day: "F", value: 52 },
                                                    { day: "S", value: 47 },
                                                    { day: "S", value: 58 }
                                                ]}
                                                margin={{
                                                    top: 10,
                                                    right: 0,
                                                    bottom: 0,
                                                    left: 0
                                                }}>
                                                <XAxis
                                                    dataKey="day"
                                                    axisLine={false}
                                                    tickLine={false}
                                                    tick={{
                                                        fill: "rgba(204,204,255,0.3)",
                                                        fontSize: 10
                                                    }}
                                                />
                                                <Bar
                                                    dataKey="value"
                                                    fill="rgba(204,204,255,0.15)"
                                                    radius={[2, 2, 0, 0]}
                                                    label={{
                                                        position: "top",
                                                        fill: "rgba(204,204,255,0.5)",
                                                        fontSize: 9,
                                                        formatter: (value: number) => `${value}`
                                                    }}
                                                />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            </motion.div>

                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                className="col-span-1 sm:col-span-2 row-span-1 group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-4 sm:p-6 hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="flex flex-col h-full">
                                    <div className="flex items-center justify-between mb-4">
                                        <div className="flex items-center gap-2">
                                            <span className="w-2 h-2 rounded-full bg-evict-primary/80 animate-pulse" />
                                            <span className="text-sm font-medium text-evict-primary/80">
                                                Active Protection
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-evict-primary/40">
                                                Protected
                                            </span>
                                            <span className="text-xs px-2 py-1 bg-black/20 rounded-full text-evict-primary/30">
                                                <HiOutlineStatusOnline className="w-3 h-3" />
                                            </span>
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-3 gap-2">
                                        {[
                                            { type: "Raids", time: "2m", count: "50+" },
                                            { type: "Spam", time: "5m", count: "23" },
                                            { type: "Scams", time: "12m", count: "7" }
                                        ].map((event, i) => (
                                            <div key={i} className="bg-black/20 rounded-xl p-3">
                                                <div className="flex items-center justify-between mb-1.5">
                                                    <div className="text-xs font-medium text-white/95">
                                                        {event.type}
                                                    </div>
                                                    <span className="flex items-center gap-1 text-xs px-2 py-1 bg-black/20 rounded-full text-evict-primary/30">
                                                        <span className="w-1 h-1 bg-evict-primary/30 rounded-full animate-[pulse_2s_cubic-bezier(0,0,0.5,1)_infinite]" />
                                                        <span>{event.time} ago</span>
                                                    </span>
                                                </div>
                                                <span className="text-xl font-semibold bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent">
                                                    {event.count}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        </div>
                    </div>
                </div>

                <div className="relative py-24 -mx-[calc((100vw-100%)/2)] bg-[#0e0d0d] border-t border-white/5">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="mb-16">
                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                className="space-y-3">
                                <h2 className="text-4xl font-medium bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block mb-4">
                                    Seamless Integrations
                                </h2>
                                <p className="text-lg text-white/60 max-w-3xl">
                                    Connect your favorite services with Evict. From Spotify to
                                    Last.fm, enhance your server with powerful integrations that
                                    work seamlessly together.
                                </p>
                            </motion.div>
                        </div>

                        <div className="select-none grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true, margin: "-50px" }}
                                transition={{ duration: 0.5 }}
                                className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-6 
                                             hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="p-3 rounded-xl bg-white/5 border border-evict-primary/20">
                                        <SiSpotify className="w-6 h-6 text-evict-primary/80" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-evict-primary/90">
                                        Spotify
                                    </h3>
                                </div>
                                <div className="space-y-4">
                                    <p className="text-white/60">
                                        Share your music, sync playlists, and show off what
                                        you&apos;re listening to.
                                    </p>
                                    <div className="space-y-2">
                                        {[
                                            "Now Playing",
                                            "Rich Presence",
                                            "Track History",
                                            "Playlist Sync"
                                        ].map((feature, i) => (
                                            <div
                                                key={i}
                                                className="flex items-center gap-2 text-sm text-white/40">
                                                <span className="text-evict-primary/20">✓</span>
                                                {feature}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div
                                    className="absolute inset-0 bg-gradient-to-br from-evict-primary/5
                                 to-transparent opacity-0 group-hover:opacity-25 transition-opacity duration-500 rounded-3xl"
                                />
                            </motion.div>

                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true, margin: "-50px" }}
                                transition={{ duration: 0.5, delay: 0.1 }}
                                className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-6 
                                             hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="p-3 rounded-xl bg-white/5 border border-evict-primary/20">
                                        <FaLastfm className="w-6 h-6 text-evict-primary/80" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-evict-primary/90">
                                        LastFM
                                    </h3>
                                </div>
                                <div className="space-y-4">
                                    <p className="text-white/60">
                                        Track your music history and discover new artists with
                                        detailed statistics.
                                    </p>
                                    <div className="space-y-2">
                                        {[
                                            "Scrobbling",
                                            "Weekly Charts",
                                            "Artist Stats",
                                            "Listening Reports"
                                        ].map((feature, i) => (
                                            <div
                                                key={i}
                                                className="flex items-center gap-2 text-sm text-white/40">
                                                <span className="text-evict-primary/20">✓</span>
                                                {feature}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div
                                    className="absolute inset-0 bg-gradient-to-br from-evict-primary/5
                                 to-transparent opacity-0 group-hover:opacity-25 transition-opacity duration-500 rounded-3xl"
                                />
                            </motion.div>

                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true, margin: "-50px" }}
                                transition={{ duration: 0.5, delay: 0.2 }}
                                className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-6 
                                             hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="p-3 rounded-xl bg-white/5 border border-evict-primary/20">
                                        <FaYoutube className="w-6 h-6 text-evict-primary/80" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-evict-primary/90">
                                        YouTube
                                    </h3>
                                </div>
                                <div className="space-y-4">
                                    <p className="text-white/60">
                                        Stream high-quality music directly in your voice channels.
                                    </p>
                                    <div className="space-y-2">
                                        {[
                                            "HD Streaming",
                                            "Playlist Support",
                                            "Live Lyrics",
                                            "Smart Autoplay"
                                        ].map((feature, i) => (
                                            <div
                                                key={i}
                                                className="flex items-center gap-2 text-sm text-white/40">
                                                <span className="text-evict-primary/20">✓</span>
                                                {feature}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div
                                    className="absolute inset-0 bg-gradient-to-br from-evict-primary/5
                                 to-transparent opacity-0 group-hover:opacity-25 transition-opacity duration-500 rounded-3xl"
                                />
                            </motion.div>
                        </div>

                        <motion.div
                            initial={{ opacity: 0 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-50px" }}
                            transition={{ duration: 0.5, delay: 0.3 }}
                            className="mt-8 text-center">
                            <span className="text-white/40 text-sm">
                                More integrations coming soon
                            </span>
                        </motion.div>
                    </div>
                </div>

                <div className="relative py-24 -mx-[calc((100vw-100%)/2)] bg-[#0e0d0d] border-t border-white/5">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-16">
                            <h2 className="text-4xl font-bold mb-4 relative">
                                <span className="text-4xl font-medium bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block mb-4 relative z-10">
                                    Core Features
                                </span>
                                <div className="absolute -inset-x-8 -inset-y-4 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-teal-500/10 blur-3xl -z-10 rounded-lg" />
                            </h2>
                            <p className="text-white/60 text-lg max-w-2xl mx-auto">
                                Everything you need in one bot. From moderation to music, we&apos;ve
                                got you covered.
                            </p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-full">
                            {[
                                {
                                    icon: Shield,
                                    title: "Moderation",
                                    description: "Advanced moderation and auto-moderation tools",
                                    commands: ["ban", "timeout", "purge", "warn"],
                                    color: "purple"
                                },
                                {
                                    icon: Settings,
                                    title: "Utility",
                                    description: "Essential server management features",
                                    commands: ["userinfo", "role", "embed", "poll"],
                                    color: "blue"
                                },
                                {
                                    icon: Music,
                                    title: "Audio",
                                    description: "High quality music with filters & effects",
                                    commands: ["play", "queue", "filter", "247"],
                                    color: "green"
                                },
                                {
                                    icon: MessageSquare,
                                    title: "Social",
                                    description: "Engage your community with social features",
                                    commands: ["profile", "rep", "marry", "daily"],
                                    color: "blue"
                                },
                                {
                                    icon: Gamepad2,
                                    title: "Fun",
                                    description: "Interactive games and entertainment",
                                    commands: ["meme", "8ball", "rps", "slots"],
                                    color: "teal"
                                },
                                {
                                    icon: HeartHandshake,
                                    title: "Roleplay",
                                    description: "Express yourself with roleplay actions",
                                    commands: ["hug", "pat", "kiss", "slap"],
                                    color: "purple"
                                },
                                {
                                    icon: FaLastfm,
                                    title: "LastFM",
                                    description: "Track and share your music taste",
                                    commands: ["fm", "taste", "artist", "top"],
                                    color: "red"
                                },
                                {
                                    icon: Sparkles,
                                    title: "Economy",
                                    description: "Virtual currency and trading system",
                                    commands: ["balance", "work", "shop", "inv"],
                                    color: "teal"
                                }
                            ].map((category, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true, margin: "-50px" }}
                                    transition={{ duration: 0.5, delay: i * 0.1 }}
                                    className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl 
                                                 hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] 
                                                 shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)] h-[220px] p-5 flex flex-col">
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-3 mb-3">
                                            <div className="p-2.5 rounded-lg bg-white/5 border border-white/10">
                                                <category.icon className="w-5 h-5 text-evict-primary/80" />
                                            </div>
                                            <h3 className="text-lg font-medium text-evict-primary/90">
                                                {category.title}
                                            </h3>
                                        </div>
                                        <p className="text-white/60 text-sm mb-3 line-clamp-2">
                                            {category.description}
                                        </p>
                                    </div>
                                    <div className="mt-auto">
                                        <div className="grid grid-cols-2 gap-1.5">
                                            {category.commands.map((cmd, j) => (
                                                <div
                                                    key={j}
                                                    className="text-[13px] bg-evict-primary/5 rounded-lg px-2.5 py-1.5 text-evict-primary/60 
                                                                 group-hover:text-evict-primary/80 font-light transition-colors border border-evict-primary/10 
                                                                 truncate text-center">
                                                    /{cmd}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-evict-primary/5
                                 to-transparent opacity-0 group-hover:opacity-25 transition-opacity duration-500 rounded-3xl"
                                    />
                                </motion.div>
                            ))}
                        </div>

                        <motion.div
                            initial={{ opacity: 0 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-50px" }}
                            transition={{ duration: 0.5 }}
                            className="text-center mt-12">
                            <a
                                href="/commands"
                                className="inline-flex items-center gap-2 text-white/60 hover:text-white transition-colors group">
                                <span>Explore all commands</span>
                                <span className="text-lg group-hover:translate-x-1 transition-transform">
                                    →
                                </span>
                            </a>
                        </motion.div>
                    </div>
                </div>

                <div className="relative py-24 -mx-[calc((100vw-100%)/2)] bg-[#0e0d0d] border-t border-white/5">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="flex flex-col lg:flex-row items-center gap-16">
                            <div className="flex-1 space-y-6">
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true }}
                                    className="space-y-3">
                                    <span className="text-4xl font-medium bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block mb-4">
                                        Voicemaster Interface
                                    </span>
                                    <p className="text-white/60 text-lg max-w-xl">
                                        Powerful control for your personal voice channel, with an
                                        intuitive, built-in chat interface.
                                    </p>
                                </motion.div>

                                <div className="mt-8 grid grid-cols-2 gap-4">
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        viewport={{ once: true, margin: "-50px" }}
                                        transition={{ delay: 0.2 }}
                                        className="group p-4 rounded-2xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 border border-white/[0.05] hover:bg-white/[0.04] transition-all duration-300">
                                        <h3 className="text-sm font-medium text-evict-primary/80 mb-2 block">
                                            Flexible Layouts
                                        </h3>

                                        <p className="text-white/60 text-sm">
                                            Choose between default or dropdown layouts to match your
                                            server&apos;s style.
                                        </p>
                                    </motion.div>

                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        viewport={{ once: true, margin: "-50px" }}
                                        transition={{ delay: 0.3 }}
                                        className="group p-4 rounded-2xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 border border-white/[0.05] hover:bg-white/[0.04] transition-all duration-300">
                                        <h3 className="text-sm font-medium text-evict-primary/80 mb-2 block">
                                            Fully Customizable
                                        </h3>
                                        <p className="text-white/60 text-sm">
                                            Personalize icons, embeds, and interface elements to
                                            your preference.
                                        </p>
                                    </motion.div>

                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        viewport={{ once: true, margin: "-50px" }}
                                        transition={{ delay: 0.4 }}
                                        className="col-span-2 group p-4 rounded-2xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 border border-white/[0.05] hover:bg-white/[0.04] transition-all duration-300">
                                        <h3 className="text-sm font-medium text-evict-primary/80 mb-2 block">
                                            Easy Setup
                                        </h3>
                                        <div className="flex flex-col sm:grid sm:grid-cols-[1fr_auto_1fr_auto_1fr] items-center gap-2">
                                            <div className="flex items-center gap-2 bg-black/20 p-2 rounded-lg w-full hover:bg-black/30 transition-colors group">
                                                <span className="text-evict-primary/60">01.</span>
                                                <span className="text-white/60 text-xs group-hover:text-white/80 transition-colors">
                                                    Invite Evict
                                                </span>
                                            </div>
                                            <span className="text-evict-primary text-lg hidden sm:block font-light">
                                                →
                                            </span>
                                            <div className="flex items-center gap-2 bg-black/20 p-2 rounded-lg w-full hover:bg-black/30 transition-colors group">
                                                <span className="text-evict-primary/60">02.</span>
                                                <span className="text-white/60 text-xs group-hover:text-white/80 transition-colors">
                                                    Run setup command
                                                </span>
                                            </div>
                                            <span className="text-evict-primary text-lg hidden sm:block font-light">
                                                →
                                            </span>
                                            <div className="flex items-center gap-2 bg-black/20 p-2 rounded-lg w-full hover:bg-black/30 transition-colors group">
                                                <span className="text-evict-primary/60">03.</span>
                                                <span className="text-white/60 text-xs group-hover:text-white/80 transition-colors">
                                                    Choose layout style
                                                </span>
                                            </div>
                                        </div>
                                    </motion.div>
                                </div>
                            </div>

                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1 }}
                                viewport={{ once: true, margin: "-50px" }}
                                transition={{ duration: 0.5 }}
                                className="flex-1 relative w-full max-w-md mx-auto lg:max-w-none">
                                <div className="rounded-2xl bg-[#0A0A0B] border border-white/[0.05] overflow-hidden p-4 md:p-6">
                                    <div className="space-y-3 md:space-y-1">
                                        <div className="flex items-center gap-2 text-white/40 text-xs font-medium select-none cursor-pointer hover:text-white/60 transition-colors">
                                            <svg
                                                className="w-2.5 h-2.5"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24">
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M9 5l7 7-7 7"
                                                />
                                            </svg>
                                            <span>VOICE CHANNELS</span>
                                        </div>

                                        <div className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-white/[0.02] transition-colors cursor-pointer group">
                                            <svg
                                                className="w-4 h-4 text-white/40"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor">
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                                                />
                                            </svg>
                                            <span className="text-white/60 group-hover:text-white/80 transition-colors text-sm">
                                                Join to Create
                                            </span>
                                        </div>

                                        <div className="flex flex-col gap-1 md:gap-1.5">
                                            <div className="flex items-center gap-2 px-2 py-1.5 rounded bg-white/[0.02] group">
                                                <svg
                                                    className="w-4 h-4 text-white/40"
                                                    fill="none"
                                                    viewBox="0 0 24 24"
                                                    stroke="currentColor">
                                                    <path
                                                        strokeLinecap="round"
                                                        strokeLinejoin="round"
                                                        strokeWidth={2}
                                                        d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                                                    />
                                                </svg>
                                                <span className="text-white/80 text-sm">
                                                    adam&apos;s channel
                                                </span>
                                            </div>

                                            <div className="ml-4 space-y-1 md:space-y-1.5">
                                                {[
                                                    {
                                                        name: "evict",
                                                        avatar: "evict-marketing.png"
                                                    },
                                                    { name: "x", avatar: "accurs.png" },
                                                    { name: "fiji", avatar: "fiji.png" },
                                                    { name: "adam", avatar: "adam-dc.png" },
                                                    { name: "b", avatar: "bhop.png" }
                                                    // { name: "compile", avatar: "compile.png" }
                                                ].map((user, i) => (
                                                    <div
                                                        key={i}
                                                        className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-white/[0.02] transition-colors group">
                                                        <Image
                                                            src={`/avs/${user.avatar}`}
                                                            alt={user.name}
                                                            width={24}
                                                            height={24}
                                                            className="rounded-full w-6 h-6"
                                                        />
                                                        <span className="text-white/60 group-hover:text-white/80 transition-colors text-sm">
                                                            {user.name}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        </div>
                    </div>
                </div>

                <div className="relative py-24 -mx-[calc((100vw-100%)/2)] bg-[#0e0d0d] border-t border-white/5">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-16">
                            <h2 className="text-4xl font-bold mb-4 relative">
                                <span className="text-4xl font-medium bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block mb-4 relative z-10">
                                    Crystal Clear Audio
                                </span>
                            </h2>
                            <p className="text-white/60 text-lg max-w-2xl mx-auto">
                                Experience high-fidelity music with advanced filters, effects, and
                                seamless platform integration.
                            </p>
                        </div>

                        <div className="flex flex-col lg:flex-row items-center gap-8 lg:gap-16">
                            <div className="flex-1 relative w-full max-w-md mx-auto lg:max-w-none">
                                <div className="rounded-2xl bg-[#0A0A0B] border border-white/[0.05] overflow-hidden">
                                    <div className="p-4 sm:p-6 border-b border-white/5">
                                        <div className="flex items-center gap-4">
                                            <Image
                                                src="/kendrick.jpg"
                                                alt="Track artwork"
                                                width={64}
                                                height={64}
                                                className="rounded flex-shrink-0"
                                            />
                                            <div className="flex-1 min-w-0">
                                                <div className="text-white/80 font-medium mb-1">
                                                    Now Playing
                                                </div>
                                                <div className="text-white/60 text-sm mb-3">
                                                    luther (with sza) - Kendrick Lamar, SZA
                                                </div>

                                                <div className="space-y-1.5">
                                                    <div className="h-1 rounded-full bg-white/5">
                                                        <div className="h-full w-[45%] bg-white/20 rounded-full" />
                                                    </div>
                                                    <div className="flex justify-between text-xs text-white/40">
                                                        <span>1:45</span>
                                                        <span>3:45</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-center gap-6 mt-4">
                                            <button className="text-white/40 hover:text-white/80 transition-colors">
                                                <Shuffle className="w-3.5 h-3.5" />
                                            </button>
                                            <button className="text-white/40 hover:text-white/80 transition-colors">
                                                <FaBackward className="w-3.5 h-3.5" />
                                            </button>
                                            <button className="bg-white/5 hover:bg-white/10 transition-colors w-8 h-8 rounded-full flex items-center justify-center text-white/80">
                                                <FaPause className="w-3.5 h-3.5" />
                                            </button>
                                            <button className="text-white/40 hover:text-white/80 transition-colors">
                                                <FaForward className="w-3.5 h-3.5" />
                                            </button>
                                            <button className="text-white/40 hover:text-white/80 transition-colors">
                                                <Repeat className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    </div>

                                    <div className="p-4 sm:p-6">
                                        <div className="flex items-center justify-between mb-3">
                                            <div className="text-xs font-medium text-white/40">
                                                UP NEXT — 3 TRACKS
                                            </div>
                                            <button className="text-xs text-white/40 hover:text-white/60 transition-colors">
                                                Clear
                                            </button>
                                        </div>
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-3 p-2 rounded hover:bg-white/[0.02] transition-colors group cursor-pointer">
                                                <Image
                                                    src="/spotify/arctic.jpg"
                                                    alt="Track artwork"
                                                    width={40}
                                                    height={40}
                                                    className="rounded flex-shrink-0"
                                                />
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-white/60 text-sm truncate group-hover:text-white/80 transition-colors">
                                                        I Wanna Be Yours
                                                    </div>
                                                    <div className="text-white/40 text-xs">
                                                        Arctic Monkeys
                                                    </div>
                                                </div>
                                                <div className="text-white/30 text-xs">3:04</div>
                                            </div>

                                            <div className="flex items-center gap-3 p-2 rounded hover:bg-white/[0.02] transition-colors group cursor-pointer">
                                                <Image
                                                    src="/toashes.jpg"
                                                    alt="Track artwork"
                                                    width={40}
                                                    height={40}
                                                    className="rounded flex-shrink-0"
                                                />
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-white/60 text-sm truncate group-hover:text-white/80 transition-colors">
                                                        To Ashes and Blood
                                                    </div>
                                                    <div className="text-white/40 text-xs">
                                                        Arcane & League of Legends
                                                    </div>
                                                </div>
                                                <div className="text-white/30 text-xs">3:21</div>
                                            </div>

                                            <div className="flex items-center gap-3 p-2 rounded hover:bg-white/[0.02] transition-colors group cursor-pointer">
                                                <Image
                                                    src="/void.jpg"
                                                    alt="Track artwork"
                                                    width={40}
                                                    height={40}
                                                    className="rounded flex-shrink-0"
                                                />
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-white/60 text-sm truncate group-hover:text-white/80 transition-colors">
                                                        VOID
                                                    </div>
                                                    <div className="text-white/40 text-xs">
                                                        Melanie Martinez
                                                    </div>
                                                </div>
                                                <div className="text-white/30 text-xs">2:58</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="flex-1 w-full">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-4">
                                    <div className="group p-6 rounded-2xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 border border-white/[0.05] hover:bg-white/[0.04] transition-all duration-300">
                                        <div className="flex items-center gap-3 mb-4">
                                            <div className="p-2 rounded-xl bg-white/5 border border-evict-primary/20">
                                                <SiSpotify className="w-6 h-6 text-evict-primary/80" />
                                            </div>
                                            <h3 className="text-xl font-semibold text-evict-primary/90">
                                                Spotify
                                            </h3>
                                        </div>
                                        <div className="space-y-2">
                                            {[
                                                "Premium quality streaming",
                                                "Playlist synchronization",
                                                "Smart recommendations",
                                                "Lyrics support"
                                            ].map((feature, i) => (
                                                <div
                                                    key={i}
                                                    className="flex items-center gap-2 text-sm text-white/40">
                                                    <span className="text-evict-primary/20">✓</span>
                                                    {feature}
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="group p-6 rounded-2xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 border border-white/[0.05] hover:bg-white/[0.04] transition-all duration-300">
                                        <div className="flex items-center gap-4 mb-6">
                                            <div className="p-2 rounded-xl bg-white/5 border border-evict-primary/20">
                                                <FaYoutube className="w-6 h-6 text-evict-primary/80" />
                                            </div>
                                            <h3 className="text-xl font-semibold text-evict-primary/90">
                                                Youtube
                                            </h3>
                                        </div>
                                        <div className="space-y-2">
                                            {[
                                                "HD audio streaming",
                                                "Live stream support",
                                                "No advertisements",
                                                "Unlimited access"
                                            ].map((feature, i) => (
                                                <div
                                                    key={i}
                                                    className="flex items-center gap-2 text-sm text-white/40">
                                                    <span className="text-evict-primary/20">✓</span>
                                                    {feature}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="relative py-24 -mx-[calc((100vw-100%)/2)] bg-[#0e0d0d] border-t border-white/5">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-16">
                            <h2 className="text-4xl font-bold mb-4 relative">
                                <span className="text-4xl font-medium bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block mb-4 relative z-10">
                                    Giveaway System
                                </span>
                                <div className="absolute -inset-x-8 -inset-y-4 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-teal-500/10 blur-3xl -z-10 rounded-lg" />
                            </h2>
                            <p className="text-white/60 text-lg max-w-2xl mx-auto">
                                Create engaging giveaways with custom requirements, multiple
                                winners, and bonus entries
                            </p>
                        </div>

                        <div className="relative">
                            <div className="absolute inset-0 bg-gradient-to-r from-evict-primary/5 to-transparent opacity-30 blur-3xl rounded-full" />

                            <div className="relative z-10 grid grid-cols-1 lg:grid-cols-3 gap-6">
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ duration: 0.5 }}
                                    className="lg:col-span-2 group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-6 
                                 hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                    <div className="flex items-center gap-4 mb-6">
                                        <div className="p-3 rounded-xl bg-white/5 border border-evict-primary/20">
                                            <Gift className="w-6 h-6 text-evict-primary/80" />
                                        </div>
                                        <h3 className="text-xl font-semibold text-evict-primary/90">
                                            Active Giveaway
                                        </h3>
                                    </div>

                                    <div className="bg-black/20 rounded-xl p-6 border border-white/5">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-2 h-2 rounded-full bg-evict-primary/80 animate-pulse" />
                                                <span className="text-evict-primary/80 font-medium text-sm">
                                                    LIVE NOW
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-2 text-xs px-3 py-1 bg-black/30 rounded-full text-white/40">
                                                <Clock className="w-3 h-3" />
                                                <span>23:45:12</span>
                                            </div>
                                        </div>

                                        <div className="flex flex-col md:flex-row gap-6">
                                            <div className="flex-1">
                                                <h4 className="text-xl font-semibold text-white/90 mb-2">
                                                    🎮 $100 Steam Gift Card
                                                </h4>
                                                <p className="text-white/60 text-sm mb-4">
                                                    React with 🎮 to enter! One lucky winner will be
                                                    randomly selected when the giveaway ends.
                                                </p>

                                                <div className="grid grid-cols-2 gap-3 mb-4">
                                                    <div className="bg-white/[0.02] rounded-lg p-3 border border-white/5">
                                                        <div className="text-xs text-white/40 mb-1">
                                                            Winners
                                                        </div>
                                                        <div className="text-lg font-medium text-white/90">
                                                            1
                                                        </div>
                                                    </div>
                                                    <div className="bg-white/[0.02] rounded-lg p-3 border border-white/5">
                                                        <div className="text-xs text-white/40 mb-1">
                                                            Entries
                                                        </div>
                                                        <div className="text-lg font-medium text-white/90">
                                                            156
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className="flex items-center gap-2 text-sm text-white/40">
                                                    <span>Hosted by</span>
                                                    <span className="text-white/80">@evict</span>
                                                </div>
                                            </div>

                                            <div className="md:w-40 flex-shrink-0 flex flex-col items-center justify-center">
                                                <div className="w-32 h-32 rounded-full bg-gradient-to-br from-evict-primary/20 to-transparent flex items-center justify-center mb-3">
                                                    <div className="w-24 h-24 rounded-full bg-black/30 flex items-center justify-center">
                                                        <Gift className="w-10 h-10 text-evict-primary/60" />
                                                    </div>
                                                </div>
                                                <div className="text-center">
                                                    <div className="text-xs text-white/40 mb-1">
                                                        Time Remaining
                                                    </div>
                                                    <div className="text-lg font-medium text-white/90">
                                                        23:45:12
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>

                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ duration: 0.5, delay: 0.1 }}
                                    className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-6 
                                 hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                    <div className="flex items-center gap-4 mb-6">
                                        <div className="p-3 rounded-xl bg-white/5 border border-evict-primary/20">
                                            <Command className="w-6 h-6 text-evict-primary/80" />
                                        </div>
                                        <h3 className="text-xl font-semibold text-evict-primary/90">
                                            Quick Commands
                                        </h3>
                                    </div>

                                    <div className="space-y-3">
                                        <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:bg-black/30 transition-colors cursor-pointer group">
                                            <div className="flex items-center justify-between">
                                                <span className="text-white/80 text-sm group-hover:text-white/90 transition-colors">
                                                    Basic Giveaway
                                                </span>
                                                <span className="text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                    /giveaway start
                                                </span>
                                            </div>
                                            <div className="mt-1 text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                Start a simple giveaway with default settings
                                            </div>
                                        </div>

                                        <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:bg-black/30 transition-colors cursor-pointer group">
                                            <div className="flex items-center justify-between">
                                                <span className="text-white/80 text-sm group-hover:text-white/90 transition-colors">
                                                    Multiple Winners
                                                </span>
                                                <span className="text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                    --winners 3
                                                </span>
                                            </div>
                                            <div className="mt-1 text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                Select multiple winners for your giveaway
                                            </div>
                                        </div>

                                        <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:bg-black/30 transition-colors cursor-pointer group">
                                            <div className="flex items-center justify-between">
                                                <span className="text-white/80 text-sm group-hover:text-white/90 transition-colors">
                                                    Role Requirements
                                                </span>
                                                <span className="text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                    --require @Role
                                                </span>
                                            </div>
                                            <div className="mt-1 text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                Restrict entry to users with specific roles
                                            </div>
                                        </div>

                                        <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:bg-black/30 transition-colors cursor-pointer group">
                                            <div className="flex items-center justify-between">
                                                <span className="text-white/80 text-sm group-hover:text-white/90 transition-colors">
                                                    Bonus Entries
                                                </span>
                                                <span className="text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                    --bonus @Role:2
                                                </span>
                                            </div>
                                            <div className="mt-1 text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                Give specific roles bonus entries
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            </div>

                            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                {[
                                    {
                                        icon: <Trophy className="w-5 h-5 text-evict-primary/80" />,
                                        title: "Multiple Winners",
                                        description:
                                            "Support for multiple winners in a single giveaway"
                                    },
                                    {
                                        icon: <Users className="w-5 h-5 text-evict-primary/80" />,
                                        title: "Role Requirements",
                                        description:
                                            "Set specific role requirements for entry eligibility"
                                    },
                                    {
                                        icon: <Star className="w-5 h-5 text-evict-primary/80" />,
                                        title: "Bonus Entries",
                                        description: "Reward specific roles with bonus entries"
                                    },
                                    {
                                        icon: <Clock className="w-5 h-5 text-evict-primary/80" />,
                                        title: "Custom Duration",
                                        description: "Set custom durations from minutes to weeks"
                                    },
                                    {
                                        icon: <Crown className="w-5 h-5 text-evict-primary/80" />,
                                        title: "Server Boosters",
                                        description: "Special perks for server boosters"
                                    },
                                    {
                                        icon: (
                                            <Sparkles className="w-5 h-5 text-evict-primary/80" />
                                        ),
                                        title: "Auto-end",
                                        description: "Automatic winner selection when time expires"
                                    }
                                ].map((feature, index) => (
                                    <motion.div
                                        key={index}
                                        initial={{ opacity: 0 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        viewport={{ once: true }}
                                        transition={{ duration: 0.5, delay: 0.1 + index * 0.05 }}
                                        className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-xl p-4 
                                     hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 rounded-lg bg-white/5 border border-evict-primary/20">
                                                {feature.icon}
                                            </div>
                                            <h3 className="text-base font-medium text-white/90">
                                                {feature.title}
                                            </h3>
                                        </div>
                                        <p className="text-white/60 text-sm mt-2 ml-11">
                                            {feature.description}
                                        </p>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="relative py-24 -mx-[calc((100vw-100%)/2)] bg-[#0e0d0d] border-t border-white/5">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    {
                                        icon: FaServer,
                                        label: "Active Servers",
                                        value: stats.guilds.toLocaleString(),
                                        delay: 0
                                    },
                                    {
                                        icon: FaUsers,
                                        label: "Total Users",
                                        value: stats.users.toLocaleString(),
                                        delay: 0.1
                                    },
                                    {
                                        icon: IoTerminal,
                                        label: "Commands",
                                        value: "1,000+",
                                        delay: 0.2
                                    },
                                    {
                                        icon: HiOutlineStatusOnline,
                                        label: "Uptime",
                                        value: "99.9%",
                                        delay: 0.3
                                    }
                                ].map((stat, index) => (
                                    <motion.div
                                        key={index}
                                        initial={{ opacity: 0 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        viewport={{ once: true, margin: "-50px" }}
                                        transition={{ duration: 0.5, delay: stat.delay }}
                                        className="group relative bg-white/[0.02] border border-evict-primary/10 rounded-xl p-4 
                                                   hover:bg-evict-300/50 hover:border-evict-primary/20 transition-all duration-300">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 rounded-xl bg-white/5 border border-evict-primary/20">
                                                <stat.icon className="w-6 h-6 text-evict-primary/80" />
                                            </div>
                                            <div>
                                                <div className="text-xl font-bold text-evict-primary">
                                                    {stat.value}
                                                </div>
                                                <div className="text-xs text-evict-primary/40">
                                                    {stat.label}
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>

                            <motion.div
                                key="server-cta"
                                initial={{ opacity: 0, x: 20 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                viewport={{ once: true, margin: "-100px" }}
                                transition={{ duration: 0.4 }}
                                className="lg:pl-12 text-center lg:text-left">
                                <span className="text-4xl font-bold bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent mb-4 block">
                                    Ready to enhance your Discord server?
                                </span>
                                <p className="text-white/60 text-xl mb-2">
                                    Join thousands of servers already using Evict
                                </p>
                                <div className="flex flex-col sm:flex-row gap-2 justify-center lg:justify-start">
                                    <motion.div
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        viewport={{ once: true }}
                                        transition={{ duration: 0.2 }}>
                                        <Link
                                            href="/invite"
                                            className="px-6 py-3 bg-evict-primary text-evict-100 rounded-xl font-medium hover:bg-opacity-90 transition-all flex items-center justify-center gap-2">
                                            Add to Discord
                                            <RiExternalLinkLine className="w-4 h-4" />
                                        </Link>
                                    </motion.div>
                                    <motion.div
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        viewport={{ once: true }}
                                        transition={{ duration: 0.2 }}>
                                        <Link
                                            href="/commands"
                                            className="px-6 py-3 bg-evict-200/50 text-evict-primary rounded-xl font-medium hover:bg-evict-200/70 transition-all border border-evict-primary/20 flex items-center justify-center gap-2">
                                            <IoTerminal className="w-4 h-4" />
                                            View Commands
                                        </Link>
                                    </motion.div>
                                </div>
                            </motion.div>
                        </div>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    )
}

export default HomePage
