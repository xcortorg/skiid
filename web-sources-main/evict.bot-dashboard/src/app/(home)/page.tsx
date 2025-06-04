"use client"

import { MeshGradient } from "@/components/(global)/GradientMesh"
import { motion } from "framer-motion"
import {
    ChevronDown,
    Gamepad2,
    HeartHandshake,
    MessageSquare,
    Music,
    Settings,
    Shield,
    Sparkles
} from "lucide-react"
import Image from "next/image"
import React, { useEffect, useState } from "react"
import {
    FaGlobe,
    FaLastfm,
    FaServer,
    FaSoundcloud,
    FaSpotify,
    FaUsers,
    FaYoutube
} from "react-icons/fa"
import {
    HiGift,
    HiOutlineCog,
    HiOutlineMusicNote,
    HiOutlineShieldCheck,
    HiOutlineStatusOnline
} from "react-icons/hi"
import { IoTerminal } from "react-icons/io5"
import { RiDiscordLine, RiRobot2Line } from "react-icons/ri"

let cachedStats: any = null
let lastFetchTime: number | null = null
const CACHE_DURATION = 5 * 60 * 1000

const apiKey = ""

const HomePage = () => {
    const [stats, setStats] = useState({ users: 0, guilds: 0 })

    useEffect(() => {
        const fetchStats = async () => {
            try {
                if (cachedStats && lastFetchTime && Date.now() - lastFetchTime < CACHE_DURATION) {
                    setStats(cachedStats)
                    return
                }

                const response = await fetch(`https://api.evict.bot/status`, {
                    headers: {
                      'Authorization': apiKey
                    }
                });
                if (!response.ok) throw new Error(`API returned ${response.status}`);

                const data = await response.json()
                cachedStats = {
                    users: data.shards.reduce(
                        (acc: number, shard: any) => acc + parseInt(shard.users.replace(/,/g, "")),
                        0
                    ),
                    guilds: data.shards.reduce(
                        (acc: number, shard: any) => acc + parseInt(shard.guilds),
                        0
                    )
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
        <div className="relative w-full overflow-x-hidden">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div
                    className="fixed inset-0 z-0 pointer-events-none opacity-[0.015]"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                        backgroundRepeat: "repeat",
                        width: "100%",
                        height: "100%"
                    }}
                />

                <div
                    className="fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-white/5 via-transparent to-zinc-400/5"
                    style={{ mixBlendMode: "overlay" }}
                />

                <MeshGradient />
                <div className="min-h-screen">
                    <div className="relative flex items-center justify-center mb-12">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10 mb-16">
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.8 }}>
                                <motion.div
                                    initial={{ scale: 0.8, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    transition={{ duration: 1, ease: "easeOut" }}>
                                    <Image
                                        src="https://r2.evict.bot/evict-new.png"
                                        alt="Evict"
                                        width={200}
                                        height={200}
                                        className="mx-auto mb-8 drop-shadow-2xl"
                                        priority
                                    />
                                </motion.div>
                                <h1 className="text-6xl md:text-7xl font-bold leading-tight">
                                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-300">
                                        The Ultimate
                                    </span>
                                    <br />
                                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-gray-200 to-gray-400">
                                        Discord Experience
                                    </span>
                                </h1>
                                <p className="mt-8 text-xl text-gray-400 max-w-2xl mx-auto">
                                    Powering{" "}
                                    <span className="text-white font-semibold">
                                        {stats.guilds.toLocaleString()}
                                    </span>{" "}
                                    servers and serving{" "}
                                    <span className="text-white font-semibold">
                                        {stats.users.toLocaleString()}
                                    </span>{" "}
                                    users
                                    <br className="hidden sm:block" /> with advanced moderation,
                                    music, and utility features.
                                </p>
                                <div className="mt-10 flex flex-col sm:flex-row justify-center gap-4">
                                    <a
                                        href="/invite"
                                        className="px-8 py-3 bg-white text-black rounded-lg font-medium hover:bg-opacity-90 transition-all text-center">
                                        Add to Discord
                                    </a>
                                    <a
                                        href="/commands"
                                        className="px-8 py-3 bg-white/10 text-white rounded-lg font-medium hover:bg-white/20 transition-all text-center">
                                        View Commands
                                    </a>
                                </div>
                            </motion.div>
                        </div>
                    </div>

                    <div className="relative py-24 -mx-[calc((100vw-100%)/2)] bg-[#0A0A0B]">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                            <div className="text-center mb-16">
                                <h2 className="text-4xl font-bold mb-4 relative">
                                    <span className="bg-gradient-to-r from-white via-white/90 to-white/80 text-transparent bg-clip-text">
                                        Why Choose Evict?
                                    </span>
                                    <div className="absolute -inset-x-4 -inset-y-2 bg-white/5 blur-2xl -z-10 rounded-lg" />
                                </h2>
                                <p className="text-white/60">
                                    Experience the next generation of Discord bots
                                </p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-full">
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                    className="md:col-span-2 min-h-[600px] md:min-h-[320px] group relative bg-white/[0.02] border border-white/5 
                                             rounded-xl p-8 hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10 h-full flex flex-col">
                                        <div className="flex items-center gap-4 mb-6">
                                            <motion.div
                                                className="p-4 rounded-xl bg-white/[0.02]"
                                                whileHover={{ scale: 1.1 }}
                                                transition={{
                                                    type: "spring",
                                                    stiffness: 400,
                                                    damping: 10
                                                }}>
                                                <HiOutlineShieldCheck className="w-10 h-10" />
                                            </motion.div>
                                            <h3 className="text-2xl font-semibold text-white">
                                                Advanced Moderation
                                            </h3>
                                        </div>

                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                            <div className="space-y-6">
                                                <p className="text-white/60 leading-relaxed text-lg">
                                                    Keep your server safe with powerful moderation
                                                    tools and auto-moderation features
                                                </p>

                                                <div className="grid gap-4">
                                                    {[
                                                        {
                                                            name: "Auto-moderation filters",
                                                            description:
                                                                "Automatically detect and remove unwanted content"
                                                        },
                                                        {
                                                            name: "Warning system",
                                                            description:
                                                                "Track and manage user infractions"
                                                        },
                                                        {
                                                            name: "Anti-raid protection",
                                                            description:
                                                                "Prevent mass joins and spam attacks"
                                                        },
                                                        {
                                                            name: "Detailed logging",
                                                            description:
                                                                "Track all moderation actions"
                                                        }
                                                    ].map((feature, i) => (
                                                        <motion.div
                                                            key={i}
                                                            initial={{ opacity: 0 }}
                                                            whileInView={{ opacity: 1 }}
                                                            transition={{ delay: 0.1 * i }}
                                                            className="flex flex-col gap-1 bg-white/[0.02] p-4 rounded-lg 
                                                             hover:bg-white/[0.04] transition-colors cursor-pointer">
                                                            <div className="flex items-center gap-3">
                                                                <div className="w-2 h-2 rounded-full bg-white/20" />
                                                                <span className="text-white/80 font-medium">
                                                                    {feature.name}
                                                                </span>
                                                            </div>
                                                            <span className="text-white/40 text-sm pl-5">
                                                                {feature.description}
                                                            </span>
                                                        </motion.div>
                                                    ))}
                                                </div>
                                            </div>

                                            <div className="space-y-4">
                                                <div className="bg-black/20 rounded-lg p-4 border border-white/5">
                                                    <div className="flex items-center gap-2 mb-4">
                                                        <div className="w-2 h-2 rounded-full bg-red-500" />
                                                        <span className="text-white/60 text-sm">
                                                            Live Moderation Feed
                                                        </span>
                                                    </div>
                                                    <div className="space-y-3">
                                                        {[
                                                            {
                                                                action: "Spam detected",
                                                                user: "User#1234",
                                                                time: "2m ago"
                                                            },
                                                            {
                                                                action: "Message filtered",
                                                                user: "User#5678",
                                                                time: "5m ago"
                                                            },
                                                            {
                                                                action: "Raid prevented",
                                                                user: "Multiple users",
                                                                time: "15m ago"
                                                            },
                                                            {
                                                                action: "Warning issued",
                                                                user: "User#9012",
                                                                time: "20m ago"
                                                            }
                                                        ].map((log, i) => (
                                                            <motion.div
                                                                key={i}
                                                                initial={{ opacity: 0, x: 20 }}
                                                                whileInView={{ opacity: 1, x: 0 }}
                                                                transition={{ delay: 0.2 * i }}
                                                                className="flex flex-col gap-1">
                                                                <div className="flex items-center justify-between">
                                                                    <span className="text-white/80 text-sm">
                                                                        {log.action}
                                                                    </span>
                                                                    <span className="text-white/40 text-xs">
                                                                        {log.time}
                                                                    </span>
                                                                </div>
                                                                <div className="flex items-center gap-2">
                                                                    <div className="w-1 h-1 rounded-full bg-white/20" />
                                                                    <span className="text-white/40 text-xs">
                                                                        {log.user}
                                                                    </span>
                                                                </div>
                                                            </motion.div>
                                                        ))}
                                                    </div>
                                                </div>

                                                <div className="bg-black/20 rounded-lg p-4 border border-white/5">
                                                    <div className="flex items-center gap-2 mb-3">
                                                        <div className="w-2 h-2 rounded-full bg-green-500" />
                                                        <span className="text-white/60 text-sm">
                                                            Server Stats
                                                        </span>
                                                    </div>
                                                    <div className="grid grid-cols-2 gap-4">
                                                        {[
                                                            {
                                                                label: "Messages Filtered",
                                                                value: "1,234"
                                                            },
                                                            {
                                                                label: "Raids Prevented",
                                                                value: "56"
                                                            },
                                                            {
                                                                label: "Warnings Issued",
                                                                value: "789"
                                                            },
                                                            {
                                                                label: "Actions Logged",
                                                                value: "2,345"
                                                            }
                                                        ].map((stat, i) => (
                                                            <motion.div
                                                                key={i}
                                                                initial={{ opacity: 0 }}
                                                                whileInView={{ opacity: 1 }}
                                                                transition={{ delay: 0.1 * i }}
                                                                className="bg-white/[0.02] rounded p-2">
                                                                <div className="text-white/40 text-xs">
                                                                    {stat.label}
                                                                </div>
                                                                <div className="text-white font-medium">
                                                                    {stat.value}
                                                                </div>
                                                            </motion.div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent 
                                                 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>

                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                    className="md:col-span-1 min-h-[500px] md:min-h-[320px] group relative bg-white/[0.02] border border-white/5 
                                             rounded-xl p-8 hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10 h-full flex flex-col">
                                        <div className="flex items-center gap-4 mb-6">
                                            <motion.div
                                                className="p-4 rounded-xl bg-white/[0.02]"
                                                whileHover={{ scale: 1.1 }}
                                                transition={{
                                                    type: "spring",
                                                    stiffness: 400,
                                                    damping: 10
                                                }}>
                                                <HiOutlineMusicNote className="w-8 h-8" />
                                            </motion.div>
                                            <h3 className="text-xl font-semibold text-white">
                                                Premium Music
                                            </h3>
                                        </div>

                                        <p className="text-white/60 leading-relaxed mb-8">
                                            High-quality music playback with support for multiple
                                            platforms including Spotify, YouTube, and SoundCloud.
                                            Enjoy crystal-clear audio.
                                        </p>

                                        <div className="space-y-6 overflow-hidden">
                                            <div className="bg-black/20 rounded-lg p-4 border border-white/5">
                                                <div className="flex items-center gap-3 mb-4">
                                                    <div className="relative w-12 h-12 rounded-md overflow-hidden flex-shrink-0">
                                                        <Image
                                                            src="/kendrick.jpg"
                                                            alt="Album Cover"
                                                            fill
                                                            className="object-cover"
                                                        />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-white font-medium truncate">
                                                            luther (with sza)
                                                        </div>
                                                        <div className="text-white/60 text-sm truncate">
                                                            Kendrick Lamar, SZA
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                                                    <motion.div
                                                        className="h-full bg-white/20 rounded-full"
                                                        initial={{ width: "0%" }}
                                                        animate={{ width: "65%" }}
                                                        transition={{
                                                            duration: 30,
                                                            repeat: Infinity
                                                        }}
                                                    />
                                                </div>
                                            </div>

                                            <div className="space-y-2">
                                                {[
                                                    {
                                                        name: "VOID",
                                                        source: "Spotify",
                                                        time: "3:45",
                                                        image: "/void.jpg"
                                                    },
                                                    {
                                                        name: "To Ashes and Blood",
                                                        source: "YouTube",
                                                        time: "4:20",
                                                        image: "/toashes.jpg"
                                                    },
                                                    {
                                                        name: "The Seed",
                                                        source: "SoundCloud",
                                                        time: "3:15",
                                                        image: "/theseed.jpg"
                                                    }
                                                ].map((track, i) => (
                                                    <motion.div
                                                        key={i}
                                                        initial={{ opacity: 0, x: -20 }}
                                                        whileInView={{ opacity: 1, x: 0 }}
                                                        transition={{ delay: 0.1 * i }}
                                                        className="flex items-center justify-between p-3 bg-white/[0.02] rounded-lg">
                                                        <div className="flex items-center gap-3">
                                                            <div className="relative w-8 h-8 rounded overflow-hidden">
                                                                <Image
                                                                    src={track.image}
                                                                    alt={track.name}
                                                                    fill
                                                                    className="object-cover"
                                                                />
                                                            </div>
                                                            <span className="text-white/60 text-sm">
                                                                {track.name}
                                                            </span>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-white/40 text-xs flex items-center gap-1">
                                                                {track.source === "Spotify" && (
                                                                    <FaSpotify className="w-3 h-3" />
                                                                )}
                                                                {track.source === "YouTube" && (
                                                                    <FaYoutube className="w-3 h-3" />
                                                                )}
                                                                {track.source === "SoundCloud" && (
                                                                    <FaSoundcloud className="w-3 h-3" />
                                                                )}
                                                                {track.source}
                                                            </span>
                                                            <span className="text-white/40 text-xs">
                                                                {track.time}
                                                            </span>
                                                        </div>
                                                    </motion.div>
                                                ))}
                                            </div>

                                            <div className="grid grid-cols-2 gap-2">
                                                {[
                                                    "High Quality",
                                                    "No Lag",
                                                    "All Platforms",
                                                    "Smart Queue"
                                                ].map((feature, i) => (
                                                    <motion.div
                                                        key={i}
                                                        initial={{ opacity: 0 }}
                                                        whileInView={{ opacity: 1 }}
                                                        transition={{ delay: 0.1 * i }}
                                                        className="text-xs bg-white/[0.02] rounded px-3 py-2 text-white/40">
                                                        {feature}
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent 
                                                 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>

                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                    className="min-h-[320px] group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                             hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-4 mb-6">
                                            <motion.div
                                                className="p-4 rounded-xl bg-white/[0.02]"
                                                whileHover={{ scale: 1.1 }}
                                                transition={{
                                                    type: "spring",
                                                    stiffness: 400,
                                                    damping: 10
                                                }}>
                                                <IoTerminal className="w-8 h-8" />
                                            </motion.div>
                                            <h3 className="text-xl font-semibold text-white">
                                                Smart Commands
                                            </h3>
                                        </div>
                                        <p className="text-white/60">
                                            Intuitive command system with smart suggestions and
                                            auto-completion
                                        </p>
                                        <div className="grid grid-cols-2 gap-2 mt-4">
                                            {["/help", "/play", "/ban", "/settings"].map(
                                                (cmd, i) => (
                                                    <motion.div
                                                        key={i}
                                                        initial={{ opacity: 0 }}
                                                        whileInView={{ opacity: 1 }}
                                                        transition={{ delay: 0.1 * i }}
                                                        className="text-sm bg-white/[0.02] rounded-lg px-3 py-2 hover:bg-white/[0.04] transition-colors cursor-pointer">
                                                        <span className="text-white/60">{cmd}</span>
                                                    </motion.div>
                                                )
                                            )}
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent 
                                                 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>

                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                    className="min-h-[320px] group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                             hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-4 mb-6">
                                            <motion.div
                                                className="p-4 rounded-xl bg-white/[0.02]"
                                                whileHover={{ scale: 1.1 }}
                                                transition={{
                                                    type: "spring",
                                                    stiffness: 400,
                                                    damping: 10
                                                }}>
                                                <RiRobot2Line className="w-8 h-8" />
                                            </motion.div>
                                            <h3 className="text-xl font-semibold text-white">
                                                Auto Moderation
                                            </h3>
                                        </div>
                                        <p className="text-white/60">
                                            Moderation that learns and adapts to your server
                                        </p>
                                        <div className="grid grid-cols-2 gap-2 mt-4">
                                            <motion.div
                                                initial={{ opacity: 0 }}
                                                whileInView={{ opacity: 1 }}
                                                className="bg-white/[0.02] rounded-lg p-3">
                                                <div className="text-2xl font-bold text-white">
                                                    99.9%
                                                </div>
                                                <div className="text-sm text-white/40">
                                                    Spam Blocked
                                                </div>
                                            </motion.div>
                                            <motion.div
                                                initial={{ opacity: 0 }}
                                                whileInView={{ opacity: 1 }}
                                                transition={{ delay: 0.1 }}
                                                className="bg-white/[0.02] rounded-lg p-3">
                                                <div className="text-2xl font-bold text-white">
                                                    &lt;8%
                                                </div>
                                                <div className="text-sm text-white/40">
                                                    False Positives
                                                </div>
                                            </motion.div>
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent 
                                                 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>

                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                    className="min-h-[320px] group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                             hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-4 mb-6">
                                            <motion.div
                                                className="p-4 rounded-xl bg-white/[0.02]"
                                                whileHover={{ scale: 1.1 }}
                                                transition={{
                                                    type: "spring",
                                                    stiffness: 400,
                                                    damping: 10
                                                }}>
                                                <HiOutlineCog className="w-8 h-8" />
                                            </motion.div>
                                            <h3 className="text-xl font-semibold text-white">
                                                Server Analytics
                                            </h3>
                                        </div>
                                        <p className="text-white/60">
                                            Detailed insights about your server&apos;s activity and
                                            growth
                                        </p>
                                        <div className="h-20 flex items-end gap-1 mt-4">
                                            {[30, 40, 45, 50, 55, 60, 65].map((value, i) => (
                                                <motion.div
                                                    key={i}
                                                    initial={{ height: 0 }}
                                                    whileInView={{ height: `${value}%` }}
                                                    transition={{ delay: i * 0.1 }}
                                                    className="flex-1 bg-white/10 rounded-t"
                                                />
                                            ))}
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-green-500/5 to-transparent 
                                                 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>
                            </div>
                        </div>
                    </div>

                    <div className="py-24">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                            <div className="text-center mb-16">
                                <h2 className="text-3xl md:text-4xl font-bold mb-4 relative">
                                    <span
                                        className="bg-gradient-to-r from-white via-white/90 to-white/80 text-transparent bg-clip-text 
                                           drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
                                        Advanced Features
                                    </span>
                                    <div className="absolute -inset-x-4 -inset-y-2 bg-white/5 blur-2xl -z-10 rounded-lg" />
                                </h2>
                                <p className="text-white/60 text-lg">
                                    Powerful tools to enhance your Discord experience
                                </p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-full">
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                    className="md:col-span-3 group relative bg-white/[0.02] border border-white/5 rounded-xl p-8 
                                             hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-4 mb-8">
                                            <motion.div
                                                className="p-4 rounded-xl bg-white/[0.02]"
                                                whileHover={{ scale: 1.1 }}
                                                transition={{
                                                    type: "spring",
                                                    stiffness: 400,
                                                    damping: 10
                                                }}>
                                                <HiGift className="w-8 h-8 text-pink-400" />
                                            </motion.div>
                                            <h3 className="text-2xl font-semibold text-white">
                                                Advanced Giveaway System
                                            </h3>
                                        </div>

                                        <div className="grid md:grid-cols-2 gap-8">
                                            <div className="space-y-4">
                                                <p className="text-white/60 leading-relaxed">
                                                    Create engaging giveaways with custom
                                                    requirements, multiple winners, and bonus
                                                    entries
                                                </p>

                                                <div className="bg-black/20 rounded-lg p-4 font-mono text-sm">
                                                    <motion.div
                                                        initial={{ opacity: 0 }}
                                                        whileInView={{ opacity: 1 }}
                                                        className="text-white/80">
                                                        ;giveaway start
                                                        <span className="text-blue-400">
                                                            {" "}
                                                            #announcements
                                                        </span>
                                                        <span className="text-green-400">
                                                            {" "}
                                                            Nitro
                                                        </span>
                                                        <span className="text-purple-400">
                                                            {" "}
                                                            --winners 3
                                                        </span>
                                                        <span className="text-yellow-400">
                                                            {" "}
                                                            --bonus @Booster:2
                                                        </span>
                                                    </motion.div>
                                                </div>

                                                <div className="grid grid-cols-2 gap-3">
                                                    {[
                                                        "Multiple winners",
                                                        "Role requirements",
                                                        "Bonus entries",
                                                        "Custom duration",
                                                        "Server boosters",
                                                        "Auto-end"
                                                    ].map((feature, i) => (
                                                        <motion.div
                                                            key={i}
                                                            initial={{ opacity: 0 }}
                                                            whileInView={{ opacity: 1 }}
                                                            transition={{ delay: 0.1 * i }}
                                                            className="flex items-center gap-2 text-sm bg-white/[0.02] rounded-lg px-3 py-2">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-pink-400/60" />
                                                            <span className="text-white/60">
                                                                {feature}
                                                            </span>
                                                        </motion.div>
                                                    ))}
                                                </div>
                                            </div>

                                            <div className="bg-black/20 rounded-lg p-6 border border-white/5">
                                                <div className="flex items-center gap-3 mb-4">
                                                    <div className="w-2 h-2 rounded-full bg-pink-500" />
                                                    <span className="text-pink-400 font-semibold">
                                                        GIVEAWAY
                                                    </span>
                                                </div>

                                                <h4 className="text-xl font-semibold text-white mb-3">
                                                    Nitro Giveaway! 🎉
                                                </h4>

                                                <div className="space-y-4">
                                                    <div className="text-white/60 text-sm space-y-2">
                                                        <p>React with 🎉 to enter!</p>
                                                        <p>
                                                            Ends in:{" "}
                                                            <span className="text-white">
                                                                24 hours
                                                            </span>
                                                        </p>
                                                        <p>
                                                            Winners:{" "}
                                                            <span className="text-white">3</span>
                                                        </p>
                                                    </div>

                                                    <div className="space-y-2">
                                                        <div className="text-sm text-white/40">
                                                            Bonus Entries:
                                                        </div>
                                                        <motion.div
                                                            initial={{ opacity: 0 }}
                                                            whileInView={{ opacity: 1 }}
                                                            className="flex items-center gap-2 text-sm bg-white/[0.02] rounded px-3 py-2">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-pink-400/60" />
                                                            <span className="text-white/60">
                                                                Server Boosters (2x entries)
                                                            </span>
                                                        </motion.div>
                                                    </div>

                                                    <div className="flex items-center justify-between text-sm text-white/40">
                                                        <span>Hosted by @evict</span>
                                                        <span>89 entries</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-pink-500/5 to-transparent 
                                                 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>

                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                    className="md:col-span-3 group relative bg-white/[0.02] border border-white/5 rounded-xl p-8 
                                             hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-4 mb-6">
                                            <span className="text-2xl">⭐</span>
                                            <h3 className="text-2xl font-semibold text-white">
                                                Custom Starboard System
                                            </h3>
                                        </div>

                                        <p className="text-white/60 mb-8">
                                            Create multiple starboards with custom emojis and
                                            thresholds
                                        </p>

                                        <div className="grid md:grid-cols-2 gap-8">
                                            <div className="space-y-6">
                                                <div className="bg-black/20 rounded-lg p-4 font-mono text-sm">
                                                    <div className="text-white/80">
                                                        ;starboard add{" "}
                                                        <span className="text-yellow-400">
                                                            #skullboard
                                                        </span>{" "}
                                                        💀{" "}
                                                        <span className="text-purple-400">
                                                            --threshold 3
                                                        </span>{" "}
                                                        <span className="text-green-400">
                                                            --self_star
                                                        </span>
                                                    </div>
                                                </div>

                                                <div className="grid grid-cols-2 gap-2">
                                                    {[
                                                        ["Custom emojis", "Multiple boards"],
                                                        [
                                                            "Adjustable threshold",
                                                            "Self-star option"
                                                        ],
                                                        ["Channel specific", "Reaction tracking"]
                                                    ].map((row, i) => (
                                                        <React.Fragment key={i}>
                                                            {row.map((feature, j) => (
                                                                <div
                                                                    key={j}
                                                                    className="text-sm bg-white/[0.02] rounded px-3 py-2 text-white/40">
                                                                    {feature}
                                                                </div>
                                                            ))}
                                                        </React.Fragment>
                                                    ))}
                                                </div>
                                            </div>

                                            <div className="bg-black/20 rounded-lg p-6">
                                                <div className="text-yellow-400 text-sm mb-4">
                                                    #skullboard
                                                </div>
                                                <div className="space-y-4">
                                                    <div className="bg-black/40 rounded-lg p-4">
                                                        <div className="flex items-start gap-3">
                                                            <div className="w-8 h-8 rounded-full overflow-hidden">
                                                                <Image
                                                                    src="https://r2.evict.bot/ba4326aff26bae608592599e14db1239.png"
                                                                    alt="x14c's avatar"
                                                                    width={32}
                                                                    height={32}
                                                                    className="object-cover w-full h-full"
                                                                />
                                                            </div>
                                                            <div className="flex-1">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-white">
                                                                        x14c
                                                                    </span>
                                                                    <span className="text-white/40 text-xs">
                                                                        Today at 17:26
                                                                    </span>
                                                                </div>
                                                                <p className="text-white/80 text-sm mt-1">
                                                                    its a man hanging sideways on a
                                                                    strip pole
                                                                </p>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div className="text-white/40 text-sm text-center">
                                                        Messages with 3+ 💀 reactions will appear
                                                        here
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-yellow-500/5 to-transparent 
                                                 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>

                                <div className="md:col-span-3 flex flex-col md:flex-row gap-4">
                                    <motion.div
                                        initial={{ opacity: 0, y: 20 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.5 }}
                                        className="w-full md:w-[400px] group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                                 hover:border-white/10 transition-all duration-300 overflow-hidden">
                                        <div className="relative z-10">
                                            <div className="flex items-center gap-4 mb-4">
                                                <span className="text-2xl">🖼️</span>
                                                <h3 className="text-xl font-semibold text-white">
                                                    Profile Database
                                                </h3>
                                            </div>

                                            <p className="text-white/60 text-sm mb-6">
                                                Access our curated collection of over 9,000 profile
                                                pictures and banners
                                            </p>

                                            <div>
                                                <div className="flex items-center gap-2 mb-4">
                                                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                                                    <span className="text-white/60 text-sm">
                                                        Latest Additions
                                                    </span>
                                                </div>

                                                <div className="space-y-3 mb-4">
                                                    <div className="bg-black/40 rounded-lg p-3">
                                                        <div className="text-white/80 text-sm mb-2">
                                                            Cats • id: 0162
                                                        </div>
                                                        <div className="aspect-[16/9] rounded-lg bg-white/5 overflow-hidden">
                                                            <Image
                                                                src="/banner1.webp"
                                                                alt="Banner"
                                                                width={320}
                                                                height={140}
                                                                className="object-cover w-full h-full"
                                                            />
                                                        </div>
                                                        <div className="text-white/40 text-xs mt-2">
                                                            discord.gg/evict
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-3">
                                                        <div className="bg-black/40 rounded-lg p-3">
                                                            <div className="text-white/80 text-sm mb-2">
                                                                girls • id: 0010
                                                            </div>
                                                            <div className="aspect-square rounded-lg bg-white/5 overflow-hidden">
                                                                <Image
                                                                    src="/pfp1.webp"
                                                                    alt="Profile"
                                                                    width={180}
                                                                    height={180}
                                                                    className="object-cover w-full h-full"
                                                                />
                                                            </div>
                                                            <div className="text-white/40 text-xs mt-2">
                                                                discord.gg/evict
                                                            </div>
                                                        </div>
                                                        <div className="bg-black/40 rounded-lg p-3">
                                                            <div className="text-white/80 text-sm mb-2">
                                                                girls • id: 0011
                                                            </div>
                                                            <div className="aspect-square rounded-lg bg-white/5 overflow-hidden">
                                                                <Image
                                                                    src="/pfp2.webp"
                                                                    alt="Profile"
                                                                    width={180}
                                                                    height={180}
                                                                    className="object-cover w-full h-full"
                                                                />
                                                            </div>
                                                            <div className="text-white/40 text-xs mt-2">
                                                                discord.gg/evict
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className="grid grid-cols-2 gap-2">
                                                    {[
                                                        "9000+ Images",
                                                        "Categorized",
                                                        "Auto-Updates",
                                                        "Fast Delivery"
                                                    ].map((feature, i) => (
                                                        <div
                                                            key={i}
                                                            className="text-sm bg-white/[0.02] rounded px-3 py-2 text-white/40">
                                                            {feature}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                        <div
                                            className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent 
                                             opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                        />
                                    </motion.div>

                                    <motion.div
                                        initial={{ opacity: 0, y: 20 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.5 }}
                                        className="w-full flex-1 group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                                 hover:border-white/10 transition-all duration-300 overflow-hidden">
                                        <div className="relative z-10">
                                            <div className="flex items-center gap-4 mb-4">
                                                <span className="text-2xl">📱</span>
                                                <h3 className="text-xl font-semibold text-white">
                                                    Social Reposter
                                                </h3>
                                            </div>

                                            <p className="text-white/60 text-sm mb-4">
                                                Automatically share content from popular social
                                                platforms to Discord
                                            </p>

                                            <div className="bg-black/40 rounded-lg p-4 mb-4">
                                                <div className="flex items-center gap-2 mb-3">
                                                    <div className="w-8 h-8 rounded-full overflow-hidden">
                                                        <Image
                                                            src="https://r2.evict.bot/ba4326aff26bae608592599e14db1239.png"
                                                            alt="x14c's avatar"
                                                            width={32}
                                                            height={32}
                                                            className="object-cover w-full h-full"
                                                        />
                                                    </div>
                                                    <div>
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-white text-sm">
                                                                x14c
                                                            </span>
                                                            <span className="text-white/40 text-xs">
                                                                used
                                                            </span>
                                                            <span className="text-red-400 text-sm">
                                                                youtube
                                                            </span>
                                                        </div>
                                                        <div className="text-white/40 text-xs">
                                                            27/12/2024, 18:20
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="aspect-video rounded-lg bg-white/5 overflow-hidden">
                                                    <Image
                                                        src="/thumbnail.jpg"
                                                        alt="YouTube Thumbnail"
                                                        width={640}
                                                        height={360}
                                                        className="object-cover w-full h-full"
                                                    />
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-2 gap-2">
                                                {[
                                                    "Instagram",
                                                    "TikTok",
                                                    "YouTube",
                                                    "SoundCloud",
                                                    "Auto-Post",
                                                    "Multi-Channel"
                                                ].map((feature, i) => (
                                                    <div
                                                        key={i}
                                                        className="text-sm bg-white/[0.02] rounded px-3 py-2 text-white/40">
                                                        {feature}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <div
                                            className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent 
                                             opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                        />
                                    </motion.div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="relative py-24 -mx-[calc((100vw-100%)/2)] bg-[#0e0d0d]">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                            <div className="text-center mb-16">
                                <h2 className="text-4xl font-bold mb-4 relative">
                                    <span
                                        className="bg-gradient-to-r from-white via-white/90 to-white/80 text-transparent bg-clip-text 
                                           drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
                                        Seamless Integrations
                                    </span>
                                    <div className="absolute -inset-x-4 -inset-y-2 bg-white/5 blur-2xl -z-10 rounded-lg" />
                                </h2>
                                <p className="text-white/60 text-lg">
                                    Connect your favorite services with Evict
                                </p>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                    className="group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                             hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-2 mb-3">
                                            <div className="w-6 h-6 rounded-full overflow-hidden">
                                                <Image
                                                    src="https://r2.evict.bot/ba4326aff26bae608592599e14db1239.png"
                                                    alt="x14c's avatar"
                                                    width={24}
                                                    height={24}
                                                    className="object-cover"
                                                />
                                            </div>
                                            <span className="text-white text-sm">evict</span>
                                            <span className="text-xs px-1 bg-blurple text-white rounded">
                                                APP
                                            </span>
                                            <span className="text-white/40 text-xs">used</span>
                                            <span className="text-[#1e9cea] text-sm">
                                                spotify view
                                            </span>
                                        </div>

                                        <div className="bg-[#18191c] rounded-lg p-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <div>
                                                    <div className="text-[#1e9cea] text-sm flex items-center gap-2 mb-1">
                                                        <Image
                                                            src="/spotify/spotify.png"
                                                            alt="Spotify"
                                                            width={16}
                                                            height={16}
                                                            className="object-cover"
                                                        />
                                                        Now Playing
                                                    </div>

                                                    <div className="text-[#1e9cea] text-sm mb-1">
                                                        The Seed
                                                    </div>
                                                    <div className="text-white/60 text-xs mb-2">
                                                        by AURORA
                                                    </div>
                                                </div>
                                                <div className="w-16 h-16 rounded overflow-hidden flex-shrink-0">
                                                    <Image
                                                        src="/theseed.jpg"
                                                        alt="Album Cover"
                                                        width={64}
                                                        height={64}
                                                        className="object-cover w-full h-full"
                                                    />
                                                </div>
                                            </div>

                                            <div className="mb-2">
                                                <div className="text-xs text-white/60 mb-1">
                                                    Progress
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-white/60 text-xs">
                                                        01:30
                                                    </span>
                                                    <div className="flex-1 h-[3px] bg-white/10 rounded-full">
                                                        <div className="w-1/3 h-full bg-white rounded-full" />
                                                    </div>
                                                    <span className="text-white/60 text-xs">
                                                        04:26
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="text-xs text-white/60 mb-2">
                                                Status
                                                <div className="flex items-center gap-2 mt-1">
                                                    <span>⏸️ Paused</span>
                                                    <span>•</span>
                                                    <span>💻 Computer</span>
                                                </div>
                                            </div>

                                            <div className="bg-[#111214] rounded p-2 mb-2 flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-white/60">💻</span>
                                                    <span className="text-white text-sm">
                                                        DESKTOP-QN6B6RP (Computer)
                                                    </span>
                                                </div>
                                                <ChevronDown className="w-4 h-4 text-white/60" />
                                            </div>

                                            <div className="flex justify-between items-center">
                                                <div className="flex gap-2">
                                                    <button className="bg-[#111214] p-2 rounded">
                                                        <Image
                                                            src="/spotify/Spotify_Previous.png"
                                                            alt="Previous"
                                                            width={20}
                                                            height={20}
                                                        />
                                                    </button>
                                                    <button className="bg-[#111214] p-2 rounded">
                                                        <Image
                                                            src="/spotify/Spotify_Pause.png"
                                                            alt="Pause"
                                                            width={20}
                                                            height={20}
                                                        />
                                                    </button>
                                                    <button className="bg-[#111214] p-2 rounded">
                                                        <Image
                                                            src="/spotify/Spotify_Next.png"
                                                            alt="Next"
                                                            width={20}
                                                            height={20}
                                                        />
                                                    </button>
                                                </div>
                                                <button className="bg-[#111214] p-2 rounded">
                                                    <Image
                                                        src="/spotify/Spotify_Volume.png"
                                                        alt="Volume"
                                                        width={20}
                                                        height={20}
                                                    />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-[#1e9cea]/5 to-transparent 
                                             opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>

                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5, delay: 0.1 }}
                                    className="group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                             hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-4 mb-6">
                                            <span className="text-2xl">
                                                <FaLastfm className="w-8 h-8 text-white/60" />
                                            </span>
                                            <h3 className="text-xl font-semibold text-white">
                                                Last.fm Integration
                                            </h3>
                                        </div>

                                        <p className="text-white/60 text-sm mb-6">
                                            Scrobble tracks and sync your music history
                                        </p>

                                        <div className="bg-black/40 rounded-lg p-4">
                                            <div className="mb-4">
                                                <h4 className="text-white font-medium mb-2">
                                                    Last.fm Connection Options
                                                </h4>
                                                <p className="text-white/60 text-sm">
                                                    How would you like to connect your Last.fm
                                                    account?
                                                </p>
                                            </div>
                                            <div className="space-y-3">
                                                <div className="flex items-center gap-3 p-3 rounded bg-white/[0.02]">
                                                    <span className="text-green-400">✅</span>
                                                    <span className="text-white/80">
                                                        Connect through web authentication
                                                        (recommended)
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-3 p-3 rounded bg-white/[0.02]">
                                                    <span className="text-red-400">❌</span>
                                                    <span className="text-white/80">Cancel</span>
                                                </div>
                                            </div>
                                            <p className="text-white/40 text-xs mt-4">
                                                Web authentication provides additional features like
                                                scrobbling and loved tracks sync
                                            </p>
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-red-500/5 to-transparent 
                                                 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>

                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5, delay: 0.2 }}
                                    className="lg:col-span-2 group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                             hover:border-white/10 transition-all duration-300 overflow-hidden">
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-4 mb-6">
                                            <span className="text-2xl">
                                                <FaGlobe className="w-8 h-8 text-white/60" />
                                            </span>
                                            <h3 className="text-xl font-semibold text-white">
                                                Web Dashboard
                                            </h3>
                                        </div>

                                        <div className="grid md:grid-cols-2 gap-6">
                                            <div>
                                                <h4 className="text-white font-medium mb-2">
                                                    Ticket Logs
                                                </h4>
                                                <p className="text-white/60 text-sm mb-4">
                                                    Access your ticket history with our aesthetic
                                                    and user-friendly web interface
                                                </p>
                                                <div className="bg-black/40 rounded-lg p-4">
                                                    <div className="flex items-center gap-3 mb-3">
                                                        <div className="w-8 h-8 rounded-full overflow-hidden">
                                                            <Image
                                                                src="https://r2.evict.bot/ba4326aff26bae608592599e14db1239.png"
                                                                alt="User avatar"
                                                                width={32}
                                                                height={32}
                                                                className="object-cover"
                                                            />
                                                        </div>
                                                        <div>
                                                            <div className="text-white text-sm">
                                                                Ticket #1234
                                                            </div>
                                                            <div className="text-white/40 text-xs">
                                                                Closed by x14c
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div className="space-y-2">
                                                        <div className="bg-white/[0.02] rounded p-2 text-sm text-white/60">
                                                            View transcript
                                                        </div>
                                                        <div className="bg-white/[0.02] rounded p-2 text-sm text-white/60">
                                                            Download attachments
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div>
                                                <h4 className="text-white font-medium mb-2">
                                                    Leaderboards
                                                </h4>
                                                <p className="text-white/60 text-sm mb-4">
                                                    Track server activity and engagement with
                                                    beautiful web leaderboards
                                                </p>
                                                <div className="bg-black/40 rounded-lg p-4">
                                                    <div className="space-y-3">
                                                        <div className="flex items-center gap-3 bg-white/[0.02] rounded-lg p-3">
                                                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-yellow-400 to-yellow-600 flex items-center justify-center text-white text-sm">
                                                                1
                                                            </div>
                                                            <div className="flex-1">
                                                                <div className="text-white text-sm">
                                                                    x14c
                                                                </div>
                                                                <div className="text-white/40 text-xs">
                                                                    Level 100 • 50,000 XP
                                                                </div>
                                                            </div>
                                                            <div className="text-yellow-400">
                                                                🏆
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-3 bg-white/[0.02] rounded-lg p-3">
                                                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-300 to-gray-500 flex items-center justify-center text-white text-sm">
                                                                2
                                                            </div>
                                                            <div className="flex-1">
                                                                <div className="text-white text-sm">
                                                                    evict
                                                                </div>
                                                                <div className="text-white/40 text-xs">
                                                                    Level 95 • 48,000 XP
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent 
                                                 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                    />
                                </motion.div>
                            </div>
                        </div>
                    </div>

                    <div className="py-24 border-t border-white/5">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                            <div className="text-center mb-16">
                                <h2 className="text-4xl font-bold mb-4 relative">
                                    <span
                                        className="bg-gradient-to-r from-white via-white/90 to-white/80 text-transparent bg-clip-text 
                                           drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
                                        Core Features
                                    </span>
                                    <div className="absolute -inset-x-4 -inset-y-2 bg-white/5 blur-2xl -z-10 rounded-lg" />
                                </h2>
                                <p className="text-white/60 text-lg">
                                    Everything you need in one bot
                                </p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-full">
                                {[
                                    {
                                        icon: Shield,
                                        title: "Moderation",
                                        description:
                                            "Advanced moderation and auto-moderation tools",
                                        commands: ["ban", "timeout", "purge", "warn"]
                                    },
                                    {
                                        icon: Settings,
                                        title: "Utility",
                                        description: "Essential server management features",
                                        commands: ["userinfo", "role", "embed", "poll"]
                                    },
                                    {
                                        icon: Music,
                                        title: "Audio",
                                        description: "High quality music with filters & effects",
                                        commands: ["play", "queue", "filter", "247"]
                                    },
                                    {
                                        icon: MessageSquare,
                                        title: "Social",
                                        description: "Engage your community with social features",
                                        commands: ["profile", "rep", "marry", "daily"]
                                    },
                                    {
                                        icon: Gamepad2,
                                        title: "Fun",
                                        description: "Interactive games and entertainment",
                                        commands: ["meme", "8ball", "rps", "slots"]
                                    },
                                    {
                                        icon: HeartHandshake,
                                        title: "Roleplay",
                                        description: "Express yourself with roleplay actions",
                                        commands: ["hug", "pat", "kiss", "slap"]
                                    },
                                    {
                                        icon: FaLastfm,
                                        title: "LastFM",
                                        description: "Track and share your music taste",
                                        commands: ["fm", "taste", "artist", "top"]
                                    },
                                    {
                                        icon: Sparkles,
                                        title: "Economy",
                                        description: "Virtual currency and trading system",
                                        commands: ["balance", "work", "shop", "inv"]
                                    }
                                ].map((category, i) => (
                                    <motion.div
                                        key={i}
                                        initial={{ opacity: 0, y: 20 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.5, delay: i * 0.1 }}
                                        className="group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                                 hover:bg-white/[0.03] hover:border-white/10 transition-all duration-300">
                                        <div className="relative z-10">
                                            <div className="mb-4">
                                                <category.icon className="w-8 h-8 text-white/60 group-hover:text-white transition-colors" />
                                            </div>
                                            <h3 className="text-xl font-semibold text-white mb-2">
                                                {category.title}
                                            </h3>
                                            <p className="text-white/60 text-sm mb-4">
                                                {category.description}
                                            </p>
                                            <div className="grid grid-cols-2 gap-2">
                                                {category.commands.map((cmd, j) => (
                                                    <div
                                                        key={j}
                                                        className="text-sm bg-black/20 rounded px-3 py-2 text-white/40 group-hover:text-white/50 transition-colors">
                                                        ;{cmd}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>

                            <div className="text-center mt-12">
                                <motion.a
                                    href="/commands"
                                    className="inline-flex items-center gap-2 text-white/60 hover:text-white transition-colors"
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}>
                                    <span>Explore all commands</span>
                                    <span className="text-lg">→</span>
                                </motion.a>
                            </div>
                        </div>
                    </div>

                    <div className="py-24 border-t border-white/5">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                                <div className="grid grid-cols-2 gap-6">
                                    <motion.div
                                        initial={{ opacity: 0, y: 20 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.5 }}
                                        className="group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                                 hover:border-white/10 transition-all duration-300 overflow-hidden">
                                        <div className="relative z-10">
                                            <div className="mb-4">
                                                <div className="flex items-center gap-3 mb-2">
                                                    <FaServer className="w-5 h-5 text-white/40" />
                                                    <div className="text-3xl font-bold text-white">
                                                        {stats.guilds.toLocaleString()}
                                                    </div>
                                                </div>
                                                <div className="text-sm text-white/40">
                                                    Active Servers
                                                </div>
                                            </div>
                                        </div>
                                        <div
                                            className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent 
                                                     opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                        />
                                    </motion.div>

                                    <motion.div
                                        initial={{ opacity: 0, y: 20 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.5, delay: 0.1 }}
                                        className="group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                                 hover:border-white/10 transition-all duration-300 overflow-hidden">
                                        <div className="relative z-10">
                                            <div className="mb-4">
                                                <div className="flex items-center gap-3 mb-2">
                                                    <FaUsers className="w-5 h-5 text-white/40" />
                                                    <div className="text-3xl font-bold text-white">
                                                        {stats.users.toLocaleString()}
                                                    </div>
                                                </div>
                                                <div className="text-sm text-white/40">
                                                    Total Users
                                                </div>
                                            </div>
                                        </div>
                                        <div
                                            className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent 
                                                     opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                        />
                                    </motion.div>

                                    <motion.div
                                        initial={{ opacity: 0, y: 20 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.5, delay: 0.2 }}
                                        className="group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                                 hover:border-white/10 transition-all duration-300 overflow-hidden">
                                        <div className="relative z-10">
                                            <div className="mb-4">
                                                <div className="flex items-center gap-3 mb-2">
                                                    <IoTerminal className="w-5 h-5 text-white/40" />
                                                    <div className="text-3xl font-bold text-white">
                                                        1,000+
                                                    </div>
                                                </div>
                                                <div className="text-sm text-white/40">
                                                    Commands
                                                </div>
                                            </div>
                                        </div>
                                        <div
                                            className="absolute inset-0 bg-gradient-to-br from-green-500/5 to-transparent 
                                                     opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                        />
                                    </motion.div>

                                    <motion.div
                                        initial={{ opacity: 0, y: 20 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.5, delay: 0.3 }}
                                        className="group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 
                                                 hover:border-white/10 transition-all duration-300 overflow-hidden">
                                        <div className="relative z-10">
                                            <div className="mb-4">
                                                <div className="flex items-center gap-3 mb-2">
                                                    <HiOutlineStatusOnline className="w-5 h-5 text-white/40" />
                                                    <div className="text-3xl font-bold text-white">
                                                        99.9%
                                                    </div>
                                                </div>
                                                <div className="text-sm text-white/40">
                                                    Uptime
                                                </div>
                                            </div>
                                        </div>
                                        <div
                                            className="absolute inset-0 bg-gradient-to-br from-red-500/5 to-transparent 
                                                     opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                        />
                                    </motion.div>
                                </div>

                                <motion.div
                                    initial={{ opacity: 0, x: 20 }}
                                    whileInView={{ opacity: 1, x: 0 }}
                                    transition={{ duration: 0.5, delay: 0.4 }}
                                    className="lg:pl-12">
                                    <h2 className="text-4xl font-bold text-white mb-6">
                                        Ready to enhance your Discord server?
                                    </h2>
                                    <p className="text-white/60 text-xl mb-10">
                                        Join thousands of servers already using Evict
                                    </p>
                                    <div className="flex flex-col sm:flex-row gap-4">
                                        <motion.a
                                            href="/invite"
                                            className="group px-8 py-3 bg-white text-black rounded-lg font-medium hover:bg-opacity-90 
                                                     transition-all flex items-center justify-center gap-2"
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}>
                                            <RiRobot2Line className="w-5 h-5" />
                                            Add to Discord
                                            <motion.span
                                                className="inline-block"
                                                initial={{ x: 0 }}
                                                whileHover={{ x: 3 }}>
                                                →
                                            </motion.span>
                                        </motion.a>
                                        <motion.a
                                            href="https://discord.gg/evict"
                                            target="_blank"
                                            className="group px-8 py-3 bg-[#5865F2] text-white rounded-lg font-medium 
                                                     hover:bg-opacity-90 transition-all flex items-center justify-center gap-2"
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}>
                                            <RiDiscordLine className="w-5 h-5" />
                                            Join our Discord
                                        </motion.a>
                                    </div>
                                </motion.div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default HomePage
