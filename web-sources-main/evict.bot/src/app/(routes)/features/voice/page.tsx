"use client"

import { AnimatePresence, motion } from "framer-motion"
import {
    Activity,
    Building2,
    Crown,
    Headphones,
    Lock,
    MessageSquare,
    Music2,
    PiggyBank,
    Repeat,
    Settings,
    Shuffle,
    Sparkles,
    Trophy,
    Users,
    Volume2
} from "lucide-react"
import Image from "next/image"
import Link from "next/link"
import { useEffect, useRef, useState } from "react"
import { FaBackward, FaForward, FaList, FaMusic, FaPause, FaPlay, FaTimes } from "react-icons/fa"
import { IoTerminal } from "react-icons/io5"
import { RiExternalLinkLine, RiSpotifyFill } from "react-icons/ri"

export default function VoiceFeature() {
    const [activeTrack, setActiveTrack] = useState({
        title: "I Wanna Be Yours",
        artist: "Arctic Monkeys",
        album: "AM",
        image: "/spotify/arctic.jpg",
        progress: 33,
        duration: "03:03",
        currentTime: "01:41",
        isPlaying: true,
        volume: 80,
        queue: [
            { title: "Luther", artist: "Kendrick Lamar, SZA", image: "/kendrick.jpg" },
            { title: "To Ashes and Blood", artist: "League of Legends", image: "/toashes.jpg" },
            { title: "VOID", artist: "Melanie Martinez", image: "/void.jpg" }
        ],
        lyrics: [
            { time: 0, text: "Baby, we both know" },
            { time: 12, text: "That the nights were mainly made for saying" },
            { time: 24, text: "Things that you can't say tomorrow day" },
            { time: 36, text: "Crawling back to you" },
            { time: 48, text: "Ever thought of calling when" },
            { time: 60, text: "You've had a few?" },
            { time: 72, text: "'Cause I always do" },
            { time: 84, text: "Maybe I'm too busy being yours" },
            { time: 96, text: "To fall for somebody new" },
            { time: 108, text: "Now I've thought it through" }
        ]
    })

    const [showQueue, setShowQueue] = useState(false)
    const [showLyrics, setShowLyrics] = useState(false)
    const [activeLyricIndex, setActiveLyricIndex] = useState(2)
    const lyricsContainerRef = useRef<HTMLDivElement>(null)
    const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true)
    const [voiceChannels, setVoiceChannels] = useState([
        { id: 1, name: "Gaming Lounge", users: 3, isLocked: false },
        { id: 2, name: "Music Room", users: 2, isLocked: true },
        { id: 3, name: "Chill Zone", users: 5, isLocked: false },
        { id: 3, name: "Chill Zone", users: 5, isLocked: false }
    ])

    useEffect(() => {
        if (!showLyrics || !isAutoScrollEnabled) return

        const timer = setInterval(() => {
            setActiveLyricIndex(prev => {
                if (prev >= activeTrack.lyrics.length - 1) return 0
                return prev + 1
            })
        }, 3000)

        return () => clearInterval(timer)
    }, [showLyrics, isAutoScrollEnabled, activeTrack.lyrics.length])

    useEffect(() => {
        if (!lyricsContainerRef.current || !showLyrics || !isAutoScrollEnabled) return

        const scrollToActiveLyric = () => {
            const container = lyricsContainerRef.current
            if (!container) return

            const activeElement = container.querySelector(`[data-index="${activeLyricIndex}"]`)
            if (!activeElement) return

            const containerHeight = container.clientHeight
            const elementTop = activeElement.getBoundingClientRect().top
            const containerTop = container.getBoundingClientRect().top
            const elementRelativeTop = elementTop - containerTop
            const targetScroll = container.scrollTop + elementRelativeTop - containerHeight / 2

            container.scrollTo({
                top: targetScroll,
                behavior: "smooth"
            })
        }

        const timeoutId = setTimeout(scrollToActiveLyric, 100)
        return () => clearTimeout(timeoutId)
    }, [activeLyricIndex, showLyrics, isAutoScrollEnabled])

    return (
        <div className="min-h-screen bg-gradient-to-b from-[#0A0A0B] to-black">
            <div className="relative border-b border-white/5">
                <div className="absolute inset-0 bg-[url('/noise.png')] opacity-5" />
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-24 pt-24 relative">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="text-center">
                        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 md:mb-6 mt-12">
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
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mb-12 md:mb-20">
                    {[
                        {
                            icon: <Music2 className="w-6 h-6 text-evict-primary" />,
                            title: "Music Integration",
                            description:
                                "Play high-quality music from multiple sources including Spotify and YouTube"
                        },
                        {
                            icon: <Headphones className="w-6 h-6 text-evict-primary" />,
                            title: "Dynamic Voice",
                            description:
                                "Create and manage voice channels with custom permissions and settings"
                        },
                        {
                            icon: <Activity className="w-6 h-6 text-evict-primary" />,
                            title: "Rich Presence",
                            description: "Share your music and activities with server members"
                        },
                        {
                            icon: <Users className="w-6 h-6 text-evict-primary" />,
                            title: "Listen Together",
                            description: "Synchronize music playback with friends in real-time"
                        },
                        {
                            icon: <Lock className="w-6 h-6 text-evict-primary" />,
                            title: "Private Sessions",
                            description: "Create private voice channels with custom access controls"
                        },
                        {
                            icon: <Settings className="w-6 h-6 text-evict-primary" />,
                            title: "Advanced Controls",
                            description: "Fine-tune audio settings and channel configurations"
                        }
                    ].map((feature, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: index * 0.1 }}
                            className="group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 hover:border-white/10 
                                     transition-all duration-300 overflow-hidden">
                            <div className="relative z-10">
                                <div className="p-3 bg-gradient-to-br from-white/10 to-transparent rounded-xl w-fit mb-4">
                                    {feature.icon}
                                </div>
                                <h3 className="text-xl font-semibold text-white mb-2">
                                    {feature.title}
                                </h3>
                                <p className="text-white/60">{feature.description}</p>
                            </div>
                            <div
                                className="absolute inset-0 bg-gradient-to-br from-evict-primary/5 to-transparent 
                                          opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                            />
                        </motion.div>
                    ))}
                </div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-[#0D0D0E] rounded-lg border border-white/5 overflow-hidden">
                        <div className="flex flex-col lg:flex-row">
                            <div className="flex-1 p-6">
                                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-8">
                                    <div className="flex items-center gap-3">
                                        <motion.button
                                            whileHover={{ scale: 1.05 }}
                                            whileTap={{ scale: 0.95 }}
                                            className="p-2.5 rounded-xl bg-gradient-to-br from-white/10 to-white/5 border border-white/10">
                                            <Music2 className="w-5 h-5 text-evict-primary" />
                                        </motion.button>
                                        <motion.button
                                            whileHover={{ scale: 1.05 }}
                                            whileTap={{ scale: 0.95 }}
                                            className="p-2.5 rounded-xl bg-gradient-to-br from-white/10 to-white/5 border border-white/10">
                                            <RiSpotifyFill className="w-5 h-5 text-green-400" />
                                        </motion.button>
                                    </div>
                                    <div className="relative w-full sm:flex-1">
                                        <input
                                            type="text"
                                            className="w-full bg-[#18191c] rounded-xl px-4 py-2.5 pl-10 text-sm text-white/80 placeholder-white/40
                                                     border border-white/5 focus:border-evict-primary/50 transition-colors outline-none"
                                            placeholder="Search songs, artists, or playlists..."
                                        />
                                        <svg
                                            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor">
                                            <path
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                strokeWidth={2}
                                                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                                            />
                                        </svg>
                                    </div>
                                </div>

                                <div className="grid lg:grid-cols-[1fr,300px] gap-8">
                                    <div>
                                        <div className="flex items-start gap-6 mb-8">
                                            <motion.div
                                                whileHover={{ scale: 1.02 }}
                                                className="relative w-48 h-48 rounded-lg overflow-hidden shadow-2xl">
                                                <Image
                                                    src={activeTrack.image}
                                                    alt={activeTrack.title}
                                                    fill
                                                    className="object-cover"
                                                />
                                                <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                                            </motion.div>
                                            <div className="flex-1">
                                                <span className="text-sm text-evict-primary uppercase tracking-wider font-medium mb-2 block">
                                                    Now Playing
                                                </span>
                                                <h3 className="text-3xl font-bold text-white mb-2">
                                                    {activeTrack.title}
                                                </h3>
                                                <p className="text-white/60 mb-4">
                                                    {activeTrack.artist} • {activeTrack.album}
                                                </p>
                                                <div className="flex flex-wrap gap-3">
                                                    <motion.button
                                                        whileHover={{ scale: 1.02 }}
                                                        whileTap={{ scale: 0.98 }}
                                                        className="px-6 py-2.5 bg-evict-primary text-white rounded-xl font-medium 
                                                                 hover:bg-opacity-90 transition-all flex items-center gap-2">
                                                        {activeTrack.isPlaying ? (
                                                            <>
                                                                <FaPause className="w-4 h-4" />
                                                                Pause
                                                            </>
                                                        ) : (
                                                            <>
                                                                <FaPlay className="w-4 h-4" />
                                                                Play
                                                            </>
                                                        )}
                                                    </motion.button>
                                                    <motion.button
                                                        whileHover={{ scale: 1.02 }}
                                                        whileTap={{ scale: 0.98 }}
                                                        onClick={() => setShowQueue(!showQueue)}
                                                        className={`px-6 py-2.5 bg-white/10 text-white rounded-xl font-medium 
                                                                 hover:bg-white/20 transition-all flex items-center gap-2
                                                                 ${showQueue ? "bg-white/20" : ""}`}>
                                                        <FaList className="w-4 h-4" />
                                                        Queue
                                                    </motion.button>
                                                    <motion.button
                                                        whileHover={{ scale: 1.02 }}
                                                        whileTap={{ scale: 0.98 }}
                                                        onClick={() => setShowLyrics(!showLyrics)}
                                                        className={`px-6 py-2.5 bg-white/10 text-white rounded-xl font-medium 
                                                                 hover:bg-white/20 transition-all flex items-center gap-2
                                                                 ${showLyrics ? "bg-white/20" : ""}`}>
                                                        <FaMusic className="w-4 h-4" />
                                                        Lyrics
                                                    </motion.button>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="space-y-6">
                                            <div className="flex items-center gap-4">
                                                <span className="text-sm text-white/40">
                                                    {activeTrack.currentTime}
                                                </span>
                                                <div className="flex-1 relative">
                                                    <div className="absolute inset-y-0 -left-2 -right-2">
                                                        <div
                                                            className="w-full h-full bg-gradient-to-r from-evict-primary/20 to-white/5 opacity-0 
                                                                      hover:opacity-100 transition-opacity rounded-full"
                                                        />
                                                    </div>
                                                    <div className="relative h-1 bg-white/10 rounded-full">
                                                        <div
                                                            className="absolute inset-y-0 left-0 bg-gradient-to-r from-evict-primary to-white/40 rounded-full"
                                                            style={{
                                                                width: `${activeTrack.progress}%`
                                                            }}
                                                        />
                                                        <motion.div
                                                            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg"
                                                            style={{
                                                                left: `${activeTrack.progress}%`
                                                            }}
                                                            whileHover={{ scale: 1.2 }}
                                                            whileTap={{ scale: 0.9 }}
                                                        />
                                                    </div>
                                                </div>
                                                <span className="text-sm text-white/40">
                                                    {activeTrack.duration}
                                                </span>
                                            </div>

                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-4">
                                                    <motion.button
                                                        whileHover={{ scale: 1.1 }}
                                                        whileTap={{ scale: 0.9 }}
                                                        className="p-2 rounded-lg hover:bg-white/5 text-white/60 hover:text-white/80">
                                                        <Shuffle className="w-5 h-5" />
                                                    </motion.button>
                                                    <motion.button
                                                        whileHover={{ scale: 1.1 }}
                                                        whileTap={{ scale: 0.9 }}
                                                        className="p-2 rounded-lg hover:bg-white/5 text-white/60 hover:text-white/80">
                                                        <FaBackward className="w-5 h-5" />
                                                    </motion.button>
                                                    <motion.button
                                                        whileHover={{ scale: 1.1 }}
                                                        whileTap={{ scale: 0.9 }}
                                                        className="p-3 rounded-full bg-white text-black hover:bg-white/90">
                                                        {activeTrack.isPlaying ? (
                                                            <FaPause className="w-5 h-5" />
                                                        ) : (
                                                            <FaPlay className="w-5 h-5" />
                                                        )}
                                                    </motion.button>
                                                    <motion.button
                                                        whileHover={{ scale: 1.1 }}
                                                        whileTap={{ scale: 0.9 }}
                                                        className="p-2 rounded-lg hover:bg-white/5 text-white/60 hover:text-white/80">
                                                        <FaForward className="w-5 h-5" />
                                                    </motion.button>
                                                    <motion.button
                                                        whileHover={{ scale: 1.1 }}
                                                        whileTap={{ scale: 0.9 }}
                                                        className="p-2 rounded-lg hover:bg-white/5 text-white/60 hover:text-white/80">
                                                        <Repeat className="w-5 h-5" />
                                                    </motion.button>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <Volume2 className="w-4 h-4 text-white/60" />
                                                    <div className="w-24 h-1 bg-white/10 rounded-full">
                                                        <div
                                                            className="h-full bg-white/40 rounded-full"
                                                            style={{
                                                                width: `${activeTrack.volume}%`
                                                            }}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <AnimatePresence mode="wait">
                                        {showQueue || showLyrics ? (
                                            <div className="relative">
                                                {showQueue ? (
                                                    <motion.div
                                                        key="queue"
                                                        initial={{ opacity: 0, x: 20 }}
                                                        animate={{ opacity: 1, x: 0 }}
                                                        exit={{ opacity: 0, x: 20 }}
                                                        className="bg-black/20 rounded-xl p-4 border border-white/5">
                                                        <div className="flex items-center justify-between mb-4">
                                                            <h4 className="text-white font-medium">
                                                                Up Next
                                                            </h4>
                                                            <button className="text-xs text-white/40 hover:text-white/60">
                                                                Clear Queue
                                                            </button>
                                                        </div>
                                                        <div className="space-y-3">
                                                            {activeTrack.queue.map(
                                                                (track, index) => (
                                                                    <motion.div
                                                                        key={index}
                                                                        initial={{
                                                                            opacity: 0,
                                                                            y: 10
                                                                        }}
                                                                        animate={{
                                                                            opacity: 1,
                                                                            y: 0
                                                                        }}
                                                                        transition={{
                                                                            delay: index * 0.1
                                                                        }}
                                                                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 group cursor-pointer">
                                                                        <div className="relative w-10 h-10 rounded overflow-hidden">
                                                                            <Image
                                                                                src={track.image}
                                                                                alt={track.title}
                                                                                fill
                                                                                className="object-cover"
                                                                            />
                                                                        </div>
                                                                        <div className="flex-1 min-w-0">
                                                                            <div className="text-sm text-white/80 truncate group-hover:text-white">
                                                                                {track.title}
                                                                            </div>
                                                                            <div className="text-xs text-white/40 truncate">
                                                                                {track.artist}
                                                                            </div>
                                                                        </div>
                                                                        <button className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-white/10">
                                                                            <FaTimes className="w-3.5 h-3.5 text-white/60" />
                                                                        </button>
                                                                    </motion.div>
                                                                )
                                                            )}
                                                        </div>
                                                    </motion.div>
                                                ) : showLyrics ? (
                                                    <motion.div
                                                        key="lyrics"
                                                        initial={{ opacity: 0, y: 20 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        exit={{ opacity: 0, y: 20 }}
                                                        className="sticky top-4 bg-gradient-to-b from-black/40 to-black/20 backdrop-blur-xl 
                                                                 rounded-xl border border-white/10 overflow-hidden w-full shadow-2xl">
                                                        <div className="p-4 border-b border-white/5 relative">
                                                            <div className="absolute inset-0 bg-gradient-to-r from-evict-primary/5 to-transparent opacity-50" />
                                                            <div className="relative flex items-center justify-between">
                                                                <div className="flex items-center gap-3">
                                                                    <div className="relative w-10 h-10 rounded-lg overflow-hidden">
                                                                        <Image
                                                                            src={activeTrack.image}
                                                                            alt={activeTrack.title}
                                                                            fill
                                                                            className="object-cover"
                                                                        />
                                                                        <div className="absolute inset-0 bg-black/20" />
                                                                    </div>
                                                                    <div>
                                                                        <h4 className="text-white font-medium text-sm">
                                                                            {activeTrack.title}
                                                                        </h4>
                                                                        <p className="text-white/60 text-xs">
                                                                            {activeTrack.artist}
                                                                        </p>
                                                                    </div>
                                                                </div>
                                                                <div className="flex items-center gap-2">
                                                                    <motion.div
                                                                        animate={{
                                                                            scale: [1, 1.2, 1],
                                                                            opacity: [0.5, 1, 0.5]
                                                                        }}
                                                                        transition={{
                                                                            duration: 2,
                                                                            repeat: Infinity,
                                                                            ease: "easeInOut"
                                                                        }}
                                                                        className="w-1.5 h-1.5 rounded-full bg-green-400"
                                                                    />
                                                                    <span className="text-[10px] uppercase tracking-wider text-green-400/80 font-medium">
                                                                        Synced
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <div className="relative h-[280px] overflow-hidden">
                                                            <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/20 pointer-events-none z-10" />
                                                            <div className="absolute inset-x-0 top-0 h-12 bg-gradient-to-b from-black/40 to-transparent pointer-events-none z-10" />
                                                            <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/40 to-transparent pointer-events-none z-10" />
                                                            <div
                                                                ref={lyricsContainerRef}
                                                                className="h-full overflow-y-auto px-4 scrollbar-none">
                                                                <div className="py-6 space-y-6">
                                                                    {activeTrack.lyrics.map(
                                                                        (line, index) => (
                                                                            <motion.div
                                                                                key={index}
                                                                                data-index={index}
                                                                                initial={{
                                                                                    opacity: 0
                                                                                }}
                                                                                animate={{
                                                                                    opacity: 1,
                                                                                    color:
                                                                                        index ===
                                                                                        activeLyricIndex
                                                                                            ? "rgb(255, 255, 255)"
                                                                                            : "rgba(255, 255, 255, 0.4)"
                                                                                }}
                                                                                transition={{
                                                                                    duration: 0.3
                                                                                }}
                                                                                className={`transition-all duration-300 px-2 py-1 rounded-lg
                                                                                ${
                                                                                    index ===
                                                                                    activeLyricIndex
                                                                                        ? "text-base font-medium bg-white/5 shadow-lg"
                                                                                        : "text-sm opacity-40 hover:opacity-60 cursor-pointer"
                                                                                }`}
                                                                                onClick={() => {
                                                                                    setActiveLyricIndex(
                                                                                        index
                                                                                    )
                                                                                    setIsAutoScrollEnabled(
                                                                                        false
                                                                                    )
                                                                                }}>
                                                                                <div className="relative group">
                                                                                    {index ===
                                                                                        activeLyricIndex && (
                                                                                        <motion.div
                                                                                            layoutId="activeLyric"
                                                                                            className="absolute -inset-2 bg-gradient-to-r from-evict-primary/10 to-transparent 
                                                                                                 rounded-lg -z-10"
                                                                                        />
                                                                                    )}
                                                                                    <div className="flex items-center gap-3">
                                                                                        <span className="text-[10px] tabular-nums opacity-50 font-mono">
                                                                                            {String(
                                                                                                line.time
                                                                                            ).padStart(
                                                                                                2,
                                                                                                "0"
                                                                                            )}
                                                                                            :00
                                                                                        </span>
                                                                                        <span>
                                                                                            {
                                                                                                line.text
                                                                                            }
                                                                                        </span>
                                                                                    </div>
                                                                                </div>
                                                                            </motion.div>
                                                                        )
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <div className="p-3 border-t border-white/5 bg-black/20">
                                                            <div className="flex items-center justify-between">
                                                                <button
                                                                    onClick={() =>
                                                                        setIsAutoScrollEnabled(
                                                                            !isAutoScrollEnabled
                                                                        )
                                                                    }
                                                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-all duration-300
                                                                              ${
                                                                                  isAutoScrollEnabled
                                                                                      ? "bg-green-400/10 text-green-400"
                                                                                      : "bg-white/5 text-white/40 hover:bg-white/10"
                                                                              }`}>
                                                                    <motion.div
                                                                        animate={
                                                                            isAutoScrollEnabled
                                                                                ? {
                                                                                      scale: [
                                                                                          1, 1.2, 1
                                                                                      ],
                                                                                      opacity: [
                                                                                          0.5, 1,
                                                                                          0.5
                                                                                      ]
                                                                                  }
                                                                                : {}
                                                                        }
                                                                        transition={{
                                                                            duration: 2,
                                                                            repeat: Infinity,
                                                                            ease: "easeInOut"
                                                                        }}
                                                                        className={`w-1.5 h-1.5 rounded-full ${
                                                                            isAutoScrollEnabled
                                                                                ? "bg-green-400"
                                                                                : "bg-white/40"
                                                                        }`}
                                                                    />
                                                                    <span className="text-[10px] uppercase tracking-wider font-medium">
                                                                        Auto-scroll{" "}
                                                                        {isAutoScrollEnabled
                                                                            ? "on"
                                                                            : "off"}
                                                                    </span>
                                                                </button>
                                                                <div className="flex items-center gap-2">
                                                                    <motion.button
                                                                        whileHover={{ scale: 1.1 }}
                                                                        whileTap={{ scale: 0.95 }}
                                                                        className="p-2 rounded-full hover:bg-white/10 text-white/40 hover:text-white/60 transition-colors">
                                                                        <svg
                                                                            className="w-3.5 h-3.5"
                                                                            fill="none"
                                                                            viewBox="0 0 24 24"
                                                                            stroke="currentColor">
                                                                            <path
                                                                                strokeLinecap="round"
                                                                                strokeLinejoin="round"
                                                                                strokeWidth={2}
                                                                                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                                                                            />
                                                                        </svg>
                                                                    </motion.button>
                                                                    <motion.button
                                                                        whileHover={{ scale: 1.1 }}
                                                                        whileTap={{ scale: 0.95 }}
                                                                        className="p-2 rounded-full hover:bg-white/10 text-white/40 hover:text-white/60 transition-colors">
                                                                        <svg
                                                                            className="w-3.5 h-3.5"
                                                                            fill="none"
                                                                            viewBox="0 0 24 24"
                                                                            stroke="currentColor">
                                                                            <path
                                                                                strokeLinecap="round"
                                                                                strokeLinejoin="round"
                                                                                strokeWidth={2}
                                                                                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                                                                            />
                                                                        </svg>
                                                                    </motion.button>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </motion.div>
                                                ) : null}
                                            </div>
                                        ) : null}
                                    </AnimatePresence>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent mb-2">
                                        VoiceMaster
                                    </h2>
                                    <p className="text-white/60">
                                        Your personal voice channel control center
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
                            <div className="space-y-6">
                                <div className="bg-gradient-to-b from-black/40 to-black/20 backdrop-blur-xl rounded-xl border border-white/10">
                                    <div className="p-4 border-b border-white/5">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className="p-2 rounded-lg bg-evict-primary/10 border border-evict-primary/20">
                                                    <Volume2 className="w-4 h-4 text-evict-primary" />
                                                </div>
                                                <span className="text-sm font-medium text-white">
                                                    Active Channels
                                                </span>
                                            </div>
                                            <span className="text-xs px-2 py-1 rounded-full bg-evict-primary/10 text-evict-primary border border-evict-primary/20">
                                                3 Active
                                            </span>
                                        </div>
                                    </div>
                                    <div className="divide-y divide-white/5">
                                        {voiceChannels.map(channel => (
                                            <motion.div
                                                key={channel.id}
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                                className="group">
                                                <div className="flex items-center gap-3 p-4 hover:bg-white/5 transition-colors cursor-pointer">
                                                    <div className="relative flex-shrink-0">
                                                        {channel.users > 0 ? (
                                                            <div className="relative">
                                                                <Volume2 className="w-4 h-4 text-evict-primary" />
                                                                <motion.div
                                                                    animate={{
                                                                        scale: [1, 1.2, 1],
                                                                        opacity: [0.3, 0.6, 0.3]
                                                                    }}
                                                                    transition={{
                                                                        duration: 2,
                                                                        repeat: Infinity,
                                                                        ease: "easeInOut"
                                                                    }}
                                                                    className="absolute -inset-1 bg-evict-primary/20 rounded-full -z-10"
                                                                />
                                                            </div>
                                                        ) : (
                                                            <Volume2 className="w-4 h-4 text-white/40" />
                                                        )}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-sm text-white/90 truncate group-hover:text-white transition-colors">
                                                                {channel.name}
                                                            </span>
                                                            {channel.isLocked && (
                                                                <Lock className="w-3.5 h-3.5 text-evict-primary/80" />
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-2 mt-1">
                                                            <div className="flex -space-x-2">
                                                                {[
                                                                    ...Array(
                                                                        Math.min(channel.users, 3)
                                                                    )
                                                                ].map((_, i) => (
                                                                    <div
                                                                        key={i}
                                                                        className="w-5 h-5 rounded-full border-2 border-[#0A0A0B] bg-white/10"
                                                                    />
                                                                ))}
                                                            </div>
                                                            {channel.users > 3 && (
                                                                <span className="text-xs text-white/40">
                                                                    +{channel.users - 3} more
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <motion.button
                                                        whileHover={{ scale: 1.05 }}
                                                        whileTap={{ scale: 0.95 }}
                                                        className="p-2 rounded-lg bg-evict-primary/10 hover:bg-evict-primary/20 
                                                                 border border-evict-primary/20 opacity-0 group-hover:opacity-100 transition-all">
                                                        <Settings className="w-4 h-4 text-evict-primary" />
                                                    </motion.button>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                    <div className="p-3 border-t border-white/5">
                                        <motion.button
                                            whileHover={{ scale: 1.01 }}
                                            whileTap={{ scale: 0.99 }}
                                            className="w-full flex items-center justify-center gap-2 p-2.5 rounded-lg 
                                                     bg-evict-primary/10 hover:bg-evict-primary/20 border border-evict-primary/20
                                                     text-evict-primary transition-all">
                                            <Crown className="w-4 h-4" />
                                            <span className="text-sm font-medium">
                                                Create New Channel
                                            </span>
                                        </motion.button>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-gradient-to-b from-black/40 to-black/20 backdrop-blur-xl rounded-xl border border-white/10 p-6">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="p-2 rounded-lg bg-evict-primary/10 border border-evict-primary/20">
                                        <IoTerminal className="w-4 h-4 text-evict-primary" />
                                    </div>
                                    <span className="text-sm font-medium text-white">
                                        Quick Commands
                                    </span>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {[
                                        {
                                            icon: Lock,
                                            label: "Lock",
                                            description: "Lock the voice channel"
                                        },
                                        {
                                            icon: Lock,
                                            label: "Unlock",
                                            description: "Unlock the voice channel"
                                        },
                                        {
                                            icon: MessageSquare,
                                            label: "Hide",
                                            description: "Ghost the voice channel"
                                        },
                                        {
                                            icon: MessageSquare,
                                            label: "Reveal",
                                            description: "Reveal the voice channel"
                                        },
                                        {
                                            icon: Crown,
                                            label: "Claim",
                                            description: "Claim the voice channel"
                                        },
                                        {
                                            icon: Users,
                                            label: "Kick",
                                            description: "Disconnect a member"
                                        },
                                        {
                                            icon: Sparkles,
                                            label: "Activity",
                                            description: "Start a new activity"
                                        },
                                        {
                                            icon: Settings,
                                            label: "Info",
                                            description: "View channel information"
                                        },
                                        {
                                            icon: Crown,
                                            label: "Increase",
                                            description: "Increase user limit"
                                        },
                                        {
                                            icon: Crown,
                                            label: "Decrease",
                                            description: "Decrease user limit"
                                        }
                                    ].map((command, index) => (
                                        <motion.div
                                            key={index}
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                            className="group relative bg-white/[0.02] hover:bg-white/[0.04] border border-white/5 
                                                     rounded-lg p-3 cursor-pointer transition-all duration-200">
                                            <div className="flex items-center gap-2.5">
                                                <div className="p-1.5 rounded-lg bg-evict-primary/10 border border-evict-primary/20">
                                                    <command.icon className="w-3.5 h-3.5 text-evict-primary" />
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="text-sm text-white/90 font-medium truncate">
                                                        {command.label}
                                                    </p>
                                                    <p className="text-xs text-white/40 truncate">
                                                        {command.description}
                                                    </p>
                                                </div>
                                            </div>
                                            <div
                                                className="absolute inset-0 bg-gradient-to-br from-evict-primary/5 to-transparent 
                                                          opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-lg"
                                            />
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    key="server-cta"
                    initial={{ opacity: 0, x: 20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true, margin: "-100px" }}
                    transition={{ duration: 0.4 }}
                    className="relative mt-24 lg:pl-12 text-center lg:text-left">
                    <div className="absolute inset-0 rounded-3xl bg-gradient-to-r from-evict-primary/10 via-transparent to-evict-primary/10 opacity-20 blur-3xl -z-10" />
                    <div className="relative">
                        <span className="text-4xl font-bold bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent mb-4 block">
                            Start Your Voice Journey
                        </span>
                        <div className="flex flex-col lg:flex-row items-center gap-8 mt-8">
                            <div className="flex-1 space-y-4">
                                <p className="text-white/60 text-xl">
                                    Join thousands of servers already using Evict&apos;s voice
                                    system
                                </p>
                                <div className="flex flex-wrap gap-6 justify-center lg:justify-start text-white/40">
                                    <div className="flex items-center gap-2">
                                        <PiggyBank className="w-5 h-5 text-evict-primary" />
                                        Start with 1,000 coins
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Building2 className="w-5 h-5 text-evict-primary" />
                                        Create your business
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Trophy className="w-5 h-5 text-evict-primary" />
                                        Climb leaderboards
                                    </div>
                                </div>
                            </div>
                            <div className="flex flex-col sm:flex-row gap-3">
                                <motion.div
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    viewport={{ once: true }}
                                    transition={{ duration: 0.2 }}>
                                    <Link
                                        href="/invite"
                                        className="px-6 py-3 bg-evict-primary text-evict-100 rounded-xl font-medium hover:bg-opacity-90 transition-all flex items-center justify-center gap-2 min-w-[160px]">
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
                                        className="px-6 py-3 bg-evict-200/50 text-evict-primary rounded-xl font-medium hover:bg-evict-200/70 transition-all border border-evict-primary/20 flex items-center justify-center gap-2 min-w-[160px]">
                                        <IoTerminal className="w-4 h-4" />
                                        View Commands
                                    </Link>
                                </motion.div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    )
}
