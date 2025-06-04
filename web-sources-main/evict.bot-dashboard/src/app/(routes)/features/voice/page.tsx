"use client"

import { motion } from "framer-motion"
import {
    Activity,
    Crown,
    Headphones,
    Lock,
    MessageSquare,
    Music2,
    Settings,
    Sparkles,
    Users,
    Volume2
} from "lucide-react"
import { RiSpotifyFill } from "react-icons/ri"

export default function VoiceFeature() {
    return (
        <div className="min-h-screen bg-gradient-to-b from-[#0A0A0B] to-black">
            <div className="relative border-b border-white/5">
                <div className="absolute inset-0 bg-[url('/noise.png')] opacity-5" />
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-24 relative">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8 }}
                        className="text-center">
                        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 md:mb-6">
                            <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-300">
                                Voice & Music Features
                            </span>
                        </h1>
                        <p className="text-base sm:text-lg text-gray-400 max-w-3xl mx-auto px-4">
                            Enhance your Discord experience with rich music integration, dynamic
                            voice channels, and activity sharing
                        </p>
                    </motion.div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-[#0D0D0E] rounded-lg border border-white/5 overflow-hidden">
                        <div className="flex flex-col lg:flex-row">
                            <div className="flex-1 pt-4 pr-4 pl-4 sm:pt-6 sm:pr-6 sm:pl-6">
                                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-6">
                                    <div className="flex items-center gap-2">
                                        <button className="p-2 rounded-lg bg-[#18191c]">
                                            <Music2 className="w-5 h-5 text-white/60" />
                                        </button>
                                        <button className="p-2 rounded-lg bg-[#18191c]">
                                            <RiSpotifyFill className="w-5 h-5 text-green-400" />
                                        </button>
                                    </div>
                                    <div className="w-full sm:flex-1">
                                        <input
                                            type="text"
                                            className="w-full bg-[#18191c] rounded-lg px-4 py-2 text-sm text-white/80 placeholder-white/40"
                                            placeholder="Search songs..."
                                            disabled
                                        />
                                    </div>
                                </div>

                                <div className="mb-8 sm:mb-12">
                                    <span className="text-sm text-white/60 uppercase tracking-wider">
                                        PERSONALIZED PLAYLIST
                                    </span>
                                    <h3 className="text-3xl sm:text-4xl font-bold text-white mt-2 mb-2">
                                        Your Mix #1
                                    </h3>
                                    <p className="text-white/60 mb-4">
                                        Created just for you. Updated daily.
                                    </p>
                                    <button className="px-6 sm:px-8 py-2.5 bg-white text-black rounded-full text-sm font-medium hover:bg-white/90 transition-colors">
                                        Play Now
                                    </button>
                                </div>

                                <div>
                                    <div className="flex items-center justify-between mb-4">
                                        <h4 className="text-lg font-semibold text-white">
                                            Recently Played
                                        </h4>
                                        <button className="text-sm text-white/60 hover:text-white">
                                            Show all
                                        </button>
                                    </div>
                                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 sm:gap-4">
                                        {[
                                            {
                                                title: "I Wanna Be Yours",
                                                artist: "Arctic Monkeys",
                                                image: "/spotify/arctic.jpg"
                                            },
                                            {
                                                title: "Luther",
                                                artist: "Kendrick Lamar, SZA",
                                                image: "/kendrick.jpg"
                                            },
                                            {
                                                title: "To Ashes and Blood",
                                                artist: "League of Legends",
                                                image: "/toashes.jpg"
                                            },
                                            {
                                                title: "VOID",
                                                artist: "Melanie Martinez",
                                                image: "/void.jpg"
                                            }
                                        ].map((track, index) => (
                                            <div key={index} className="group cursor-pointer">
                                                <div className="aspect-square bg-[#18191c] rounded-lg overflow-hidden mb-2">
                                                    <img
                                                        src={track.image}
                                                        alt={track.title}
                                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                                                    />
                                                </div>
                                                <div className="text-xs text-white font-medium truncate">
                                                    {track.title}
                                                </div>
                                                <div className="text-xs text-white/60 truncate">
                                                    {track.artist}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="flex-1 min-h-[130px]" />

                                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 py-2">
                                    <div className="flex items-center gap-3">
                                        <img
                                            src="/spotify/arctic.jpg"
                                            alt="Now Playing"
                                            className="w-10 h-10 rounded object-cover"
                                        />
                                        <div>
                                            <div className="text-sm text-white font-medium">
                                                I Wanna Be Yours
                                            </div>
                                            <div className="text-xs text-white/60">
                                                Arctic Monkeys
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex-1 w-full min-w-0 flex items-center gap-2">
                                        <span className="text-[11px] text-white/40">01:41</span>
                                        <div className="flex-1 h-1 bg-white/10 rounded-full">
                                            <div className="w-1/3 h-full bg-white/40 rounded-full" />
                                        </div>
                                        <span className="text-[11px] text-white/40">03:03</span>
                                    </div>
                                    <div className="flex items-center gap-2 ml-auto sm:ml-0">
                                        <button className="p-1.5 rounded-lg hover:bg-white/5">
                                            <Volume2 className="w-4 h-4 text-white/60" />
                                        </button>
                                        <button className="p-1.5 rounded-lg hover:bg-white/5">
                                            <Users className="w-4 h-4 text-white/60" />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div className="hidden lg:block w-96 border-l border-white/5">
                                <div className="h-full flex flex-col">
                                    <div className="relative h-96">
                                        <div className="absolute inset-0 flex items-center justify-center">
                                            <svg
                                                className="w-48 h-48 text-white/20"
                                                viewBox="0 0 200 100">
                                                <path
                                                    d="M0,50 C20,30 40,70 60,50 C80,30 100,70 120,50 C140,30 160,70 180,50"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    strokeWidth="2"
                                                />
                                            </svg>
                                        </div>
                                    </div>
                                    <div className="flex-1 p-6">
                                        <h3 className="text-2xl font-bold text-white mb-1">
                                            Strangers
                                        </h3>
                                        <p className="text-white/60">
                                            Kenya Grace • 771,934 monthly listeners
                                        </p>
                                        <div className="flex gap-2 mt-2">
                                            <span className="px-2 py-1 bg-[#18191c] rounded-full text-xs text-white/80">
                                                rnb
                                            </span>
                                            <span className="px-2 py-1 bg-[#18191c] rounded-full text-xs text-white/80">
                                                electronic
                                            </span>
                                            <span className="px-2 py-1 bg-[#18191c] rounded-full text-xs text-white/80">
                                                pop
                                            </span>
                                        </div>
                                        <div className="space-y-6 mt-8">
                                            {[
                                                "It's like déjà vu (it's like déjà vu)",
                                                "And when we spoke for months",
                                                "Well, did you ever mean it? (Did you ever mean it?)",
                                                "How can we say that this is love",
                                                "When it goes like this?"
                                            ].map((lyric, index) => (
                                                <div
                                                    key={index}
                                                    className={`text-lg ${index === 2 ? "text-white" : "text-white/40"}`}>
                                                    {lyric}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
                                Rich Activity Status
                            </h2>
                            <p className="text-white/60">
                                Share what you&apos;re listening to with your community
                            </p>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="bg-black/20 rounded-xl p-6 border border-white/5">
                                    <div className="flex items-start gap-3">
                                        <div className="relative">
                                            <div className="w-12 h-12 rounded-full bg-[#18191c] overflow-hidden">
                                                <img
                                                    src="https://r2.evict.bot/ba4326aff26bae608592599e14db1239.png"
                                                    alt="Profile"
                                                    className="w-full h-full object-cover"
                                                />
                                            </div>
                                            <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 border-[3px] border-[#18191c]" />
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <span className="text-white text-sm font-medium">
                                                    username
                                                </span>
                                                <span className="text-xs text-white/40">•</span>
                                                <span className="text-xs text-white/40">
                                                    he/him
                                                </span>
                                            </div>
                                            <div className="mt-2">
                                                <div className="flex items-center gap-1.5">
                                                    <RiSpotifyFill className="w-3.5 h-3.5 text-green-400" />
                                                    <span className="text-xs text-white/60">
                                                        Listening to Evict Music
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-3 mt-2">
                                                    <div className="w-12 h-12 bg-[#18191c] rounded-sm overflow-hidden flex-shrink-0">
                                                        <img
                                                            src="/spotify/arctic.jpg"
                                                            alt="Album Art"
                                                            className="w-full h-full object-cover"
                                                        />
                                                    </div>
                                                    <div className="flex-1">
                                                        <div className="text-sm text-white font-medium">
                                                            I Wanna Be Yours
                                                        </div>
                                                        <div className="text-xs text-white/60 mt-0.5">
                                                            Arctic Monkeys
                                                        </div>
                                                        <div className="flex items-center gap-2 mt-2">
                                                            <span className="text-[11px] text-white/40">
                                                                01:41
                                                            </span>
                                                            <div className="flex-1 h-1 bg-white/10 rounded-full">
                                                                <div className="w-1/3 h-full bg-white/40 rounded-full" />
                                                            </div>
                                                            <span className="text-[11px] text-white/40">
                                                                03:03
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex gap-1.5 mt-3">
                                                    <span className="px-1.5 py-0.5 bg-green-500/10 rounded text-[11px] font-medium text-green-400">
                                                        support
                                                    </span>
                                                    <span className="px-1.5 py-0.5 bg-purple-500/10 rounded text-[11px] font-medium text-purple-400">
                                                        donor
                                                    </span>
                                                    <span className="px-1.5 py-0.5 bg-blue-500/10 rounded text-[11px] font-medium text-blue-400">
                                                        developer
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <div className="bg-black/20 rounded-xl p-4 border border-white/5">
                                        <div className="flex items-center gap-3">
                                            <Activity className="w-5 h-5 text-blue-400" />
                                            <span className="text-white/80">
                                                Rich Activity Status
                                            </span>
                                        </div>
                                    </div>
                                    <div className="bg-black/20 rounded-xl p-4 border border-white/5">
                                        <div className="flex items-center gap-3">
                                            <Headphones className="w-5 h-5 text-purple-400" />
                                            <span className="text-white/80">Listen Along</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
                                VoiceMaster
                            </h2>
                            <p className="text-white/60">
                                Create and manage dynamic voice channels
                            </p>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-6">
                            <div className="col-span-1">
                                <div className="bg-black/20 rounded-xl border border-white/5">
                                    <div className="p-4 border-b border-white/5">
                                        <div className="flex items-center gap-2">
                                            <Volume2 className="w-4 h-4 text-white/60" />
                                            <span className="text-sm text-white/60">
                                                Voice Channels
                                            </span>
                                        </div>
                                    </div>
                                    <div className="p-2 space-y-1">
                                        <button className="w-full flex items-center gap-2 p-2 rounded text-white/60 hover:bg-white/5">
                                            <Crown className="w-4 h-4" />
                                            <span className="text-sm">➕ Create Channel</span>
                                        </button>
                                        <div className="flex items-center gap-2 p-2 rounded bg-white/5">
                                            <Volume2 className="w-4 h-4 text-green-400" />
                                            <span className="text-sm text-white">
                                                Gaming Lounge
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="col-span-2">
                                <div className="bg-black/20 rounded-xl border border-white/5 p-6">
                                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                                        {[
                                            {
                                                icon: Lock,
                                                label: "Lock Channel",
                                                color: "text-blue-400"
                                            },
                                            {
                                                icon: Users,
                                                label: "User Limit",
                                                color: "text-purple-400"
                                            },
                                            {
                                                icon: Settings,
                                                label: "Permissions",
                                                color: "text-amber-400"
                                            },
                                            {
                                                icon: MessageSquare,
                                                label: "Private Chat",
                                                color: "text-green-400"
                                            },
                                            {
                                                icon: Music2,
                                                label: "Music Mode",
                                                color: "text-pink-400"
                                            },
                                            {
                                                icon: Sparkles,
                                                label: "Special Access",
                                                color: "text-indigo-400"
                                            }
                                        ].map((feature, index) => (
                                            <button
                                                key={index}
                                                className="flex flex-col items-center gap-2 p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                                                <feature.icon
                                                    className={`w-5 h-5 ${feature.color}`}
                                                />
                                                <span className="text-sm text-white/80">
                                                    {feature.label}
                                                </span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    )
}
