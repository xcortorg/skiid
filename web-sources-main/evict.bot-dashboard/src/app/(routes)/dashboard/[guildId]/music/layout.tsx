// @ts-nocheck

"use client"

import { checkBetaAccess } from "@/libs/dashboard/beta"
import { DashboardResponse, DiscordGuild, fetchUserGuilds } from "@/libs/dashboard/guild"
import { navigation } from "@/libs/dashboard/navigation"
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query"
import {
    AudioWaveformIcon,
    Bell,
    ChevronDown,
    ChevronLeft,
    ChevronUp,
    GripVertical,
    Heart,
    ListMusic,
    LucideIcon,
    Maximize,
    Menu,
    Mic2,
    Pause,
    Play,
    Plus,
    RefreshCw,
    SkipBack,
    SkipForward,
    Volume2,
    X,
    AlertTriangle,
    Check,
    Info
} from "lucide-react"
import Image from "next/image"
import Link from "next/link"
import { usePathname, useRouter, useSelectedLayoutSegment } from "next/navigation"
import React, { memo, useEffect, useRef, useState } from "react"
import toast, { Toaster } from "react-hot-toast"
import { MusicContext } from "./music-context"
import { MusicProvider } from "./music-provider"
import UserAvatar from "@/components/UserAvatar"
import { format } from "date-fns"

const queryClient = new QueryClient()

interface ChildProps {
    guild?: DiscordGuild
    userGuilds?: DiscordGuild[]
}

interface NavigationItem {
    name: string
    icon: LucideIcon
    href: string
    isComingSoon?: boolean
}

interface Recommendation {
    title: string
    author: string
    artworkUrl: string
    duration: number
}

interface DeezerTrack {
    album: {
        cover_medium: string
    }
}

const artworkCache: Record<string, string> = {}

const QueueItem = memo(({ track, index }: { track: any; index: number }) => {
    const [artwork, setArtwork] = useState<string | null>(() => {
        const trackId = `${track.title}-${track.artist}`
        return artworkCache[trackId] || null
    })

    useEffect(() => {
        const getArtwork = async () => {
            const trackId = `${track.title}-${track.artist}`

            if (artworkCache[trackId]) {
                setArtwork(artworkCache[trackId])
                return
            }

            try {
                const deezerArt = await fetchDeezerArtwork(track.title, track.artist)
                if (deezerArt) {
                    artworkCache[trackId] = deezerArt
                    setArtwork(deezerArt)
                }
            } catch (error) {
                console.error("Failed to fetch artwork:", error)
            }
        }

        getArtwork()
    }, [track.title, track.artist])

    return (
        <div className="flex items-center gap-3 p-2 hover:bg-white/5 rounded-md group">
            <img src={artwork || track.thumbnail} alt="" className="w-10 h-10 rounded" />
            <div className="flex-1 min-w-0">
                <div className="text-sm text-white font-medium truncate">{track.title}</div>
                <div className="text-xs text-white/60 truncate">{track.artist}</div>
            </div>
            <button className="opacity-0 group-hover:opacity-100 transition-opacity">
                <GripVertical className="w-4 h-4 text-white/40" />
            </button>
        </div>
    )
})

QueueItem.displayName = "QueueItem"

export default function DashboardLayout({
    children,
    params
}: {
    children: React.ReactNode
    params: { guildId: string }
}) {
    const segment = useSelectedLayoutSegment()

    if (segment === "music") {
        return children
    }

    return (
        <QueryClientProvider client={queryClient}>
            <MusicProvider>
                <DashboardLayoutContent params={params}>{children}</DashboardLayoutContent>
            </MusicProvider>
            <Toaster />
        </QueryClientProvider>
    )
}

function ComingSoon() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            <h1 className="text-3xl font-bold text-white mb-4">Coming Soon</h1>
            <p className="text-white/60 max-w-md">
                We&apos;re working hard to bring you this feature. Stay tuned for updates!
            </p>
        </div>
    )
}

function DashboardLayoutContent({
    children,
    params
}: {
    children: React.ReactNode
    params: { guildId: string }
}) {
    const segment = useSelectedLayoutSegment()
    const router = useRouter()
    const pathname = usePathname()
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [isGuildSelectorOpen, setIsGuildSelectorOpen] = useState(false)
    const [showLyrics, setShowLyrics] = useState(false)
    const [isPlayerExpanded, setIsPlayerExpanded] = useState(false)
    const [showFilters, setShowFilters] = useState(false)
    const [showQueue, setShowQueue] = useState(false)
    const [recommendations, setRecommendations] = useState<Recommendation[]>([])
    const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false)
    const karaokeLineRef = useRef<HTMLDivElement>(null)

    const [playerState, setPlayerState] = useState<PlayerState>({
        current: null,
        queue: [],
        controls: {
            volume: 100,
            isPlaying: false,
            repeat: "off",
            shuffle: false
        }
    })

    const [lyrics, setLyrics] = useState<LyricsResult | null>(null)
    const [currentTime, setCurrentTime] = useState(0)
    const currentLineRef = useRef<HTMLDivElement>(null)

    const isCurrentLine = (index: number) => {
        const lyricsResult = lyrics?.results?.find(result => result.lyrics?.length > 0)
        const line = lyricsResult?.lyrics?.[index]
        const nextLine = lyricsResult?.lyrics?.[index + 1]

        const isCurrent =
            line &&
            nextLine &&
            currentTime >= line.milliseconds &&
            currentTime < nextLine.milliseconds

        if (isCurrent) {
            console.log("Current line index:", index)
        }
        return isCurrent
    }

    const isPastLine = (index: number) => {
        const lyricsResult = lyrics?.results?.find(result => result.lyrics?.length > 0)
        const line = lyricsResult?.lyrics?.[index]
        const nextLine = lyricsResult?.lyrics?.[index + 1]
        return line && nextLine && currentTime >= nextLine.milliseconds
    }

    const handleLyricSeek = (milliseconds: number) => {
        controls.seek(milliseconds)
    }

    const controls = {
        togglePlay: () => {
            // TODO: actually finish off this fucking bitch
        }
    }

    const formatTime = (ms: number) => {
        if (!ms) return "--:--"
        const totalSeconds = Math.floor(ms / 1000)
        const minutes = Math.floor(totalSeconds / 60)
        const seconds = totalSeconds % 60
        return `${minutes}:${seconds.toString().padStart(2, "0")}`
    }

    const { data: betaAccess, isError: betaError } = useQuery({
        queryKey: ["beta"],
        queryFn: checkBetaAccess,
        staleTime: 1000 * 15,
        retry: false
    })

    useEffect(() => {
        if (betaAccess && !betaAccess.has_access) {
            const currentPath = window.location.pathname
            router.push(`/login?redirect=${encodeURIComponent(currentPath)}&forBeta=true`)
        }
    }, [betaAccess, router])

    const { data: userGuilds, isLoading: guildsLoading, isError, error } = useQuery({
        queryKey: ["guilds"],
        queryFn: fetchUserGuilds,
        staleTime: 1000 * 60 * 5,
        initialData: queryClient.getQueryData(["guilds"]),
        retry: false
    })

    const currentGuild = (userGuilds as DashboardResponse)?.guilds?.find(
        g => g.id === params.guildId
    )
    const currentPage = Object.values(navigation)
        .flat()
        .find(item => pathname === `/dashboard/${currentGuild?.id}${item.href}`)

    const isComingSoonPage = currentPage?.isComingSoon

    const filteredGuilds =
        (userGuilds as DashboardResponse)?.guilds?.filter(
            g => g.permissions.manage_guild || g.permissions.admin || g.owner
        ) || []

    useEffect(() => {
        if (guildsLoading) return

        if (isError && (error as any)?.response?.status === 401) {
            router.push("/login")
            return
        }

        if (!guildsLoading && !currentGuild && (userGuilds as DashboardResponse)?.guilds) {
            router.push("/dashboard")
            return
        }
    }, [router, currentGuild, guildsLoading, isError, error, userGuilds])

    const musicContextValue = {
        playerState,
        setPlayerState,
        showLyrics,
        setShowLyrics,
        lyrics,
        setLyrics,
        currentTime,
        setCurrentTime,
        controls
    }

    useEffect(() => {
        const fetchLyrics = async () => {
            if (!playerState.current?.title || !showLyrics) return

            try {
                const [cleanTitle, cleanArtist] = cleanTitleForSearch(
                    playerState.current.title,
                    playerState.current.artist
                )

                const response = await fetch(
                    `https://listen.squareweb.app/lyrics?title=${encodeURIComponent(cleanTitle)}&artist=${encodeURIComponent(cleanArtist)}&key=evictiscool`
                )
                if (!response.ok) throw new Error("Failed to fetch lyrics")
                const data = await response.json()
                setLyrics(data)
            } catch (error) {
                console.error("Error fetching lyrics:", error)
                setLyrics(null)
            }
        }

        fetchLyrics()
    }, [showLyrics, playerState.current?.title, playerState.current?.artist])

    const cleanTitleForSearch = (title: string, artist: string): [string, string] => {
        const patterns = [
            /\[.*?\]/g,
            /\(from .*?\)/g,
            /\(Official.*?\)/g,
            /\(feat\..*?\)/g,
            /\(ft\..*?\)/g,
            /\(Explicit\)/g,
            /\(Official Video\)/g,
            /\(Audio\)/g,
            /\(Lyrics\)/g
        ]

        let cleanTitle = title
        patterns.forEach(pattern => {
            cleanTitle = cleanTitle.replace(pattern, "")
        })

        if (cleanTitle.includes(" - ")) {
            const [artistPart, titlePart] = cleanTitle.split(" - ", 2)
            if (titlePart) {
                artist = artistPart
                cleanTitle = titlePart
            }
        }

        return [cleanTitle.trim(), artist.trim()]
    }

    const [isManualScrolling, setIsManualScrolling] = useState(false)
    let scrollTimeout: NodeJS.Timeout

    useEffect(() => {
        if (currentLineRef.current && !isManualScrolling) {
            console.log("Current time:", currentTime)
            console.log("Current line ref exists:", !!currentLineRef.current)

            const containers = document.querySelectorAll(".lyrics-container")
            containers.forEach(container => {
                if (!container) return

                const lineTop = currentLineRef.current.offsetTop
                const containerHeight = container.clientHeight
                const targetScroll = lineTop - containerHeight * 0.4

                console.log("Scrolling to:", targetScroll)
                console.log("Container found:", !!container)

                container.scrollTo({
                    top: targetScroll,
                    behavior: "smooth"
                })
            })
        }
    }, [currentTime, isManualScrolling])

    useEffect(() => {
        const handleScroll = () => {
            setIsManualScrolling(true)
            clearTimeout(scrollTimeout)
            scrollTimeout = setTimeout(() => {
                setIsManualScrolling(false)
            }, 5000)
        }

        const containers = document.querySelectorAll(".lyrics-container")
        containers.forEach(container => {
            container.addEventListener("wheel", handleScroll)
            container.addEventListener("touchmove", handleScroll)
        })

        return () => {
            containers.forEach(container => {
                container.removeEventListener("wheel", handleScroll)
                container.removeEventListener("touchmove", handleScroll)
            })
            clearTimeout(scrollTimeout)
        }
    }, [])

    useEffect(() => {
        if (lyrics?.results?.[0]?.lyrics && lyrics.results[0].lyrics.length > 0) {
            const containers = document.querySelectorAll(".lyrics-container")
            containers.forEach(container => {
                container.scrollTo({ top: 0, behavior: "instant" })
            })
        }
    }, [playerState.current?.title])

    const fetchRecommendations = async () => {
        if (!playerState.current?.title) return

        setIsLoadingRecommendations(true)
        try {
            const response = await fetch(
                `https://listen.squareweb.app/autoplay?title=${encodeURIComponent(playerState.current.title)}&author=${encodeURIComponent(playerState.current.artist)}&algorithm=DYNAMIC&key=evictiscool`
            )
            const data = await response.json()
            setRecommendations(data)
        } catch (error) {
            console.error("Failed to fetch recommendations:", error)
        }
        setIsLoadingRecommendations(false)
    }

    useEffect(() => {
        fetchRecommendations()
    }, [playerState.current?.title])

    const fetchDeezerArtwork = async (title: string, artist: string): Promise<string | null> => {
        try {
            const cleanTitle = title.replace(/\([^)]*\)|\[[^\]]*\]/g, "").trim()
            const cleanArtist = artist.replace(/\([^)]*\)|\[[^\]]*\]/g, "").trim()
            const query = encodeURIComponent(`${cleanTitle} ${cleanArtist}`)

            const response = await fetch(`/api/deezer/search?q=${query}`)
            if (!response.ok) throw new Error("Deezer API request failed")

            const data = await response.json()
            return data.data?.[0]?.album?.cover_big || null
        } catch (error) {
            console.error("Failed to fetch Deezer artwork:", error)
            return null
        }
    }

    const QueueSection = () => {
        return (
            <div
                className={`
                fixed top-[70px] right-0 bottom-24 w-[400px] bg-[#111111] border-l border-white/10 
                transform transition-transform duration-300 ease-in-out overflow-hidden
                ${showQueue ? "translate-x-0" : "translate-x-full"}
                ${showLyrics ? "translate-x-[400px]" : ""}
            `}>
                <div className="h-full flex flex-col">
                    <div className="flex items-center justify-between p-4 border-b border-white/10">
                        <div className="flex gap-4">
                            <button
                                className={`text-sm font-medium ${showQueue ? "text-white" : "text-white/60"}`}>
                                Queue
                            </button>
                            <button
                                className={`text-sm font-medium ${!showQueue ? "text-white" : "text-white/60"}`}>
                                Recently played
                            </button>
                        </div>
                        <button onClick={() => setShowQueue(false)}>
                            <X className="w-5 h-5 text-white/60" />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto">
                        {playerState.current && (
                            <div className="px-4 pt-4">
                                <div className="text-xs text-white/60 font-medium mb-3">
                                    Now playing
                                </div>
                                <QueueItem track={playerState.current} index={-1} />
                            </div>
                        )}

                        {playerState.queue && playerState.queue.length > 0 && (
                            <div className="px-4 pt-6">
                                <div className="text-xs text-white/60 font-medium mb-3">
                                    Next in queue
                                </div>
                                <div className="space-y-1">
                                    {playerState.queue.map((track, i) => (
                                        <QueueItem
                                            key={`${track.title}-${track.artist}-${i}`}
                                            track={track}
                                            index={i}
                                        />
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="px-4 pt-6 pb-4">
                            <div className="flex items-center justify-between mb-3">
                                <div className="text-xs text-white/60 font-medium">Recommended</div>
                                <button
                                    onClick={fetchRecommendations}
                                    className="p-1 hover:bg-white/5 rounded transition-colors">
                                    <RefreshCw
                                        className={`w-3 h-3 text-white/40 ${isLoadingRecommendations ? "animate-spin" : ""}`}
                                    />
                                </button>
                            </div>
                            <div className="space-y-1">
                                {Array.isArray(recommendations) && recommendations.length > 0 ? (
                                    recommendations.map((track, i) => (
                                        <div
                                            key={i}
                                            className="flex items-center gap-3 p-2 hover:bg-white/5 rounded-md group">
                                            <img
                                                src={track.artworkUrl}
                                                alt=""
                                                className="w-10 h-10 rounded"
                                            />
                                            <div className="flex-1 min-w-0">
                                                <div className="text-sm text-white font-medium truncate">
                                                    {track.title}
                                                </div>
                                                <div className="text-xs text-white/60 truncate">
                                                    {track.author}
                                                </div>
                                            </div>
                                            <button className="opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Plus className="w-4 h-4 text-white/40" />
                                            </button>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-sm text-white/40 text-center py-2">
                                        No recommendations available
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    const handleQueueClick = () => {
        if (showLyrics) setShowLyrics(false)
        setShowQueue(!showQueue)
    }

    const handleLyricsClick = () => {
        if (showQueue) setShowQueue(false)
        setShowLyrics(!showLyrics)
    }

    const [isLyricsExpanded, setIsLyricsExpanded] = useState(false)

    const expandedLineRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (expandedLineRef.current && !isManualScrolling) {
            const container = document.querySelector(".expanded-lyrics-container")
            if (!container) return

            const lineTop = expandedLineRef.current.offsetTop
            const containerHeight = container.clientHeight
            const headerOffset = 300
            const targetScroll = lineTop - headerOffset - containerHeight * 0.2

            container.scrollTo({
                top: targetScroll,
                behavior: "smooth"
            })
        }
    }, [currentTime, isManualScrolling])

    const [videoUrl, setVideoUrl] = useState<string | null>(null)
    const [artistInfo, setArtistInfo] = useState<any>(null)

    useEffect(() => {
        const fetchTrackExtras = async () => {
            if (!playerState.current?.title) return

            try {
                const infoResponse = await fetch(
                    `/api/song?title=${encodeURIComponent(playerState.current.title)}&artist=${encodeURIComponent(playerState.current.artist)}`
                )
                const infoData = await infoResponse.json()
                setArtistInfo(infoData)

                if (infoData.spotify?.trackId) {
                    const videoResponse = await fetch(
                        `https://listen.squareweb.app/video?spotifyId=${infoData.spotify.trackId}&key=evictiscool`
                    )
                    const videoData = await videoResponse.json()
                    console.log("Video data:", videoData)
                    setVideoUrl(videoData.url)
                }
            } catch (error) {
                console.error("Failed to fetch track extras:", error)
                setVideoUrl(null)
            }
        }

        fetchTrackExtras()
    }, [playerState.current?.title, playerState.current?.artist])

    const [showArtistView, setShowArtistView] = useState(false)

    const [isKaraokeMode, setIsKaraokeMode] = useState(false)

    const hasRichSync = () => {
        return lyrics?.results?.some(result => result.richSync?.length > 0)
    }

    const KaraokeLine = ({ line, currentTime }) => {
        const relativeTime = currentTime - line.startTime
        const lastOffset = line.words[line.words.length - 1]?.offset || 0

        const calculateProgress = () => {
            if (relativeTime <= 0) return 0
            if (relativeTime >= lastOffset) return 100

            const currentWordIndex = line.words.findIndex((word, index) => {
                const nextWord = line.words[index + 1]
                const currentWordEnd = nextWord ? nextWord.offset : lastOffset
                return relativeTime >= word.offset && relativeTime < currentWordEnd
            })

            if (currentWordIndex === -1) return 0

            const currentWord = line.words[currentWordIndex]
            const nextWord = line.words[currentWordIndex + 1]
            const currentWordEnd = nextWord ? nextWord.offset : lastOffset

            const wordProgress =
                (relativeTime - currentWord.offset) / (currentWordEnd - currentWord.offset)
            const wordStart = (currentWord.offset / lastOffset) * 100
            const progressEnd = ((nextWord ? nextWord.offset : lastOffset) / lastOffset) * 100

            return Math.min(100, Math.max(0, wordStart + (progressEnd - wordStart) * wordProgress))
        }

        const progress = calculateProgress()

        return (
            <div
                className="text-3xl font-bold text-center whitespace-nowrap overflow-hidden"
                style={{
                    background: `linear-gradient(to right, 
                        white 0%, white ${progress}%, 
                        rgba(255,255,255,0.2) ${progress}%, rgba(255,255,255,0.2) 100%
                    )`,
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    backgroundClip: "text"
                }}>
                {line.text}
            </div>
        )
    }

    useEffect(() => {
        if (isKaraokeMode && karaokeLineRef.current && !isManualScrolling) {
            const container = document.querySelector(".expanded-lyrics-container")
            if (!container) return

            const lineTop = karaokeLineRef.current.offsetTop
            const containerHeight = container.clientHeight
            const headerOffset = 300
            const targetScroll = lineTop - headerOffset - containerHeight * 0.2

            container.scrollTo({
                top: targetScroll,
                behavior: "smooth"
            })
        }
    }, [currentTime, isKaraokeMode, isManualScrolling])

    const handleMessage = async (event: MessageEvent) => {
        try {
            const data = JSON.parse(event.data)
            console.log("🎵 Raw message received:", event.data)

            switch (data.type) {
                case "STATE_UPDATE":
                    const state = data.data
                    console.log("🎵 State update received:", state)

                    if (mountedRef.current) {
                        setPlayerState(state)

                        if (state.current) {
                            const songId = `${state.current.title}-${state.current.artist}`
                            if (songId !== lastProcessedSong.current) {
                                lastProcessedSong.current = songId
                                
                                fetchDeezerThumbnail(state.current.title, state.current.artist).then(
                                    deezerThumbnail => {
                                        if (!mountedRef.current) return
                                        
                                        if (deezerThumbnail) {
                                            setPlayerState(prevState => ({
                                                ...prevState,
                                                current: prevState.current ? {
                                                    ...prevState.current,
                                                    thumbnail: deezerThumbnail
                                                } : null
                                            }))
                                        }
                                    }
                                )
                            }
                        }

                        if (state.current?.position !== undefined) {
                            setCurrentTime(state.current.position)
                        }
                    }
                    break
            }
        } catch (error) {
            console.error("🎵 Message handling error:", error)
        }
    }

    const [isOpen, setIsOpen] = useState(false)

    if (guildsLoading) {
        return (
            <div className="min-h-screen bg-[#0A0A0B]">
                <div className="bg-[#0B0C0C] w-full h-[95px] border-b border-white/5">
                    <div className="2xl:container 2xl:mx-auto px-10 md:px-[8vw] 2xl:px-52 py-4">
                        <div className="flex items-center justify-between mt-3">
                            <div className="flex items-center gap-6">
                                <div className="w-6 h-6 bg-white/5 rounded animate-pulse" />
                                <div className="flex space-x-3">
                                    <div className="w-[35px] h-[35px] bg-white/5 rounded-lg animate-pulse" />
                                    <div className="w-24 h-8 bg-white/5 rounded animate-pulse" />
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <div className="w-5 h-5 bg-white/5 rounded animate-pulse" />
                                <div className="w-8 h-8 bg-white/5 rounded-full animate-pulse" />
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex">
                    <aside className="fixed lg:static inset-y-0 left-0 w-64 bg-[#0A0A0B] border-r border-white/5 -translate-x-full lg:translate-x-0">
                        <div className="p-4">
                            <div className="bg-white/[0.02] rounded-lg border border-white/5 p-3 animate-pulse">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-white/5 rounded-lg" />
                                    <div className="flex-1 space-y-2">
                                        <div className="h-5 bg-white/5 rounded w-3/4" />
                                        <div className="h-4 bg-white/5 rounded w-1/2" />
                                    </div>
                                </div>
                            </div>
                        </div>
                        <nav className="mt-4 px-3 space-y-6">
                            {[...Array(3)].map((_, i) => (
                                <div key={i} className="space-y-2">
                                    <div className="h-4 w-16 bg-white/5 rounded" />
                                    <div className="space-y-1">
                                        {[...Array(4)].map((_, j) => (
                                            <div key={j} className="h-10 bg-white/5 rounded-lg" />
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </nav>
                    </aside>
                    <main className="flex-1 min-h-[calc(100vh-95px)]">
                        <div className="p-6">{children}</div>
                    </main>
                </div>
            </div>
        )
    }

    return (
        <MusicContext.Provider value={musicContextValue}>
            <div className="min-h-screen bg-[#0B0C0C] flex flex-col overflow-hidden">
                <div className="bg-[#0B0C0C] w-full h-[70px] border-b border-white/5 shrink-0 fixed top-0 left-0 right-0 z-50">
                    <div className="h-full px-6 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                                className="lg:hidden text-white/60 hover:text-white transition-colors">
                                {isSidebarOpen ? (
                                    <X className="w-5 h-5" />
                                ) : (
                                    <Menu className="w-5 h-5" />
                                )}
                            </button>

                            <Link href="/" className="flex items-center gap-3">
                                <Image
                                    src="https://r2.evict.bot/evict-new.png"
                                    alt="evict"
                                    width={32}
                                    height={32}
                                    className="rounded-lg"
                                />
                                <span className="text-xl font-semibold text-white">evict</span>
                            </Link>
                        </div>

                        <div className="flex items-center gap-6">
                            <div className="relative">
                                <button 
                                    onClick={() => setIsOpen(!isOpen)} 
                                    className="text-white/60 hover:text-white transition-colors"
                                >
                                    <Bell className="w-5 h-5" />
                                    {userGuilds?.notifications?.length > 0 && (
                                        <span className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full" />
                                    )}
                                </button>

                                {isOpen && (
                                    <>
                                        <div 
                                            className="fixed inset-0 z-40" 
                                            onClick={() => setIsOpen(false)} 
                                        />
                                        <div className="absolute right-0 mt-2 w-80 bg-[#111111] border border-white/5 rounded-xl shadow-lg z-50">
                                            <div className="p-4">
                                                <h3 className="text-sm font-medium text-white">Notifications</h3>
                                                <div className="mt-2 space-y-2">
                                                    {userGuilds?.notifications?.length === 0 ? (
                                                        <p className="text-sm text-white/60">No notifications</p>
                                                    ) : (
                                                        userGuilds?.notifications?.map(notification => (
                                                            <div key={notification.id} className="p-3 bg-white/[0.02] rounded-lg">
                                                                <div className="flex items-start gap-2">
                                                                    {notification.type === "info" && <Info className="w-4 h-4 text-blue-400 mt-0.5" />}
                                                                    {notification.type === "warning" && <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5" />}
                                                                    {notification.type === "error" && <X className="w-4 h-4 text-red-400 mt-0.5" />}
                                                                    {notification.type === "success" && <Check className="w-4 h-4 text-green-400 mt-0.5" />}
                                                                    <div>
                                                                        <p className="text-sm font-medium text-white">{notification.title}</p>
                                                                        <p className="text-sm text-white/60">{notification.content}</p>
                                                                        <p className="text-xs text-white/40 mt-1">
                                                                            {format(new Date(notification.created_at), "MMM d, yyyy")}
                                                                        </p>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        ))
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </>
                                )}
                            </div>
                            <UserAvatar />
                        </div>
                    </div>
                </div>

                <div className="flex flex-1 pt-[70px]">
                    <aside
                        className={`fixed lg:static inset-y-[70px] left-0 w-64 bg-[#0A0A0B] border-r border-white/5 
                        ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"} transition-transform duration-200`}>
                        <div className={`${!isSidebarOpen ? "lg:hidden" : ""} h-full`}>
                            <button
                                onClick={() => setIsSidebarOpen(false)}
                                className="absolute right-2 top-2 p-2 hover:bg-white/5 rounded-lg transition-colors lg:hidden">
                                <X className="w-5 h-5 text-white/60" />
                            </button>

                            <div className="p-4">
                                <div
                                    className="relative"
                                    onMouseLeave={() => setIsGuildSelectorOpen(false)}>
                                    <button
                                        onClick={() =>
                                            setIsGuildSelectorOpen(!isGuildSelectorOpen)
                                        }
                                        className="w-full flex items-center gap-3 p-3 bg-white/[0.02] rounded-lg border border-white/5 hover:bg-white/[0.04] transition-colors">
                                        <Image
                                            src={
                                                currentGuild?.icon
                                                    ? `https://cdn.discordapp.com/icons/${currentGuild.id}/${currentGuild.icon}.png`
                                                    : "https://cdn.discordapp.com/embed/avatars/1.png"
                                            }
                                            alt={currentGuild?.name ?? ""}
                                            width={40}
                                            height={40}
                                            className="rounded-lg"
                                        />
                                        <div className="flex-1 truncate">
                                            <h3 className="text-white font-medium truncate">
                                                {currentGuild?.name}
                                            </h3>
                                            <p className="text-sm text-white/40">
                                                Server Settings
                                            </p>
                                        </div>
                                        <ChevronDown
                                            className={`w-5 h-5 text-white/40 transition-transform ${isGuildSelectorOpen ? "rotate-180" : ""}`}
                                        />
                                    </button>

                                    {isGuildSelectorOpen && (
                                        <>
                                            <div className="absolute left-0 right-0 h-2 -bottom-2" />
                                            <div
                                                onMouseEnter={() =>
                                                    setIsGuildSelectorOpen(true)
                                                }
                                                className="absolute top-full left-0 right-0 mt-2 py-2 bg-[#0B0C0C] border border-white/5 rounded-lg shadow-xl z-50 max-h-[300px] overflow-y-auto">
                                                {filteredGuilds.map(guild => (
                                                    <Link
                                                        key={guild.id}
                                                        href={`/dashboard/${guild.id}`}
                                                        className={`flex items-center gap-3 px-3 py-2 hover:bg-white/5 transition-colors
                                                            ${guild.id === currentGuild?.id ? "bg-white/10" : ""}`}>
                                                        <Image
                                                            src={
                                                                guild.icon
                                                                    ? `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png`
                                                                    : "https://cdn.discordapp.com/embed/avatars/1.png"
                                                            }
                                                            alt={guild.name}
                                                            width={32}
                                                            height={32}
                                                            className="rounded-lg"
                                                        />
                                                        <div className="flex-1 truncate">
                                                            <h4 className="text-sm text-white truncate">
                                                                {guild.name}
                                                            </h4>
                                                        </div>
                                                    </Link>
                                                ))}
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>

                            <nav className="mt-4 px-3">
                                <button
                                    onClick={() => setIsSidebarOpen(false)}
                                    className="w-full flex items-center gap-2 p-2 mb-4 text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                                    <ChevronLeft className="w-5 h-5" />
                                    <span className="text-sm">Collapse Sidebar</span>
                                </button>
                                {Object.entries(navigation).map(([category, items]) => (
                                    <div key={category} className="mb-6">
                                        <h4 className="px-3 mb-2 text-xs font-medium text-white/40 uppercase tracking-wider">
                                            {category}
                                        </h4>
                                        <div className="space-y-1">
                                            {items.map(item => (
                                                <Link
                                                    key={item.name}
                                                    // @ts-ignore
                                                    href={
                                                        item.isComingSoon
                                                            ? "#"
                                                            : `/dashboard/${currentGuild?.id}${item.href}`
                                                    }
                                                    onClick={e => {
                                                        if (item.isComingSoon) {
                                                            e.preventDefault()
                                                            toast.error(
                                                                "This feature is coming soon!"
                                                            )
                                                        }
                                                    }}
                                                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
                                                        ${
                                                            pathname ===
                                                            `/dashboard/${currentGuild?.id}${item.href}`
                                                                ? "bg-white/10 text-white"
                                                                : "text-white/60 hover:text-white hover:bg-white/5"
                                                        }
                                                        ${item.isComingSoon ? "opacity-50" : ""}`}>
                                                    {/* @ts-ignore */}
                                                    <item.icon className="w-4 h-4" />
                                                    <span>{item.name}</span>
                                                    {item.isComingSoon && (
                                                        <span className="ml-auto text-xs bg-white/10 px-2 py-0.5 rounded">
                                                            Soon
                                                        </span>
                                                    )}
                                                </Link>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </nav>
                        </div>
                    </aside>

                    <main
                        className={`flex-1 transition-all duration-200 
                        ${isSidebarOpen ? "lg:ml-4" : ""} 
                        ${showLyrics ? "" : ""} 
                        ${showQueue ? "mr-[400px]" : ""}
                        ${showLyrics && showQueue ? "mr-[800px]" : ""}
                    `}>
                        <div className="h-[calc(100vh-94px)] overflow-y-auto pt-6">
                            {children}
                        </div>
                    </main>

                    <aside
                        className={`
                        fixed inset-0 
                        backdrop-blur-lg bg-black/80
                        transform transition-all duration-300 ease-in-out
                        ${isLyricsExpanded ? "translate-x-0" : "translate-x-full"}
                        z-[9999]
                    `}>
                        <div className="relative h-full flex flex-col">
                            <div className="absolute top-4 right-4 z-10 flex items-center gap-4">
                                {hasRichSync() && (
                                    <button
                                        onClick={() => setIsKaraokeMode(!isKaraokeMode)}
                                        className={`text-white/60 hover:text-white transition-colors ${isKaraokeMode ? "text-evict-pink" : ""}`}>
                                        <Mic2 className="w-5 h-5" />
                                    </button>
                                )}
                                <button
                                    onClick={() => setIsLyricsExpanded(false)}
                                    className="text-white/60 hover:text-white transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <div className="flex flex-col items-center pt-16 pb-8">
                                <div className="w-32 h-32 mb-6">
                                    <img
                                        src={playerState.current?.thumbnail}
                                        alt=""
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                                <h2 className="text-2xl font-bold text-white mb-2">
                                    {playerState.current?.title}
                                </h2>
                                <p className="text-white/60">{playerState.current?.artist}</p>
                            </div>

                            <div className="flex-1 overflow-hidden">
                                <div className="h-full overflow-y-auto expanded-lyrics-container">
                                    <div className="min-h-full">
                                        {isKaraokeMode && hasRichSync()
                                            ? lyrics?.results
                                                  ?.find(result => result.richSync?.length > 0)
                                                  ?.richSync?.map((line, index) => (
                                                      <div
                                                          key={index}
                                                          ref={
                                                              currentTime >= line.startTime &&
                                                              currentTime <= line.endTime
                                                                  ? karaokeLineRef
                                                                  : null
                                                          }
                                                          className={`
                                                        px-8 py-4 transition-colors duration-300
                                                        ${currentTime >= line.startTime && currentTime <= line.endTime ? "opacity-100" : "opacity-40"}
                                                    `}>
                                                          <KaraokeLine
                                                              line={line}
                                                              currentTime={currentTime}
                                                          />
                                                      </div>
                                                  ))
                                            : lyrics?.results
                                                  ?.find(result => result.lyrics?.length > 0)
                                                  ?.lyrics?.map((line, index) => (
                                                      <div
                                                          key={index}
                                                          ref={
                                                              isCurrentLine(index)
                                                                  ? expandedLineRef
                                                                  : null
                                                          }
                                                          onClick={() =>
                                                              handleLyricSeek(line.milliseconds)
                                                          }
                                                          className={`
                                                        px-8 py-4 text-3xl text-center font-bold transition-colors duration-300 cursor-pointer
                                                        hover:text-white
                                                        ${isCurrentLine(index) ? "text-white" : isPastLine(index) ? "text-zinc-600" : "text-zinc-500"}
                                                    `}>
                                                          {line.line.trim() === ""
                                                              ? "♪"
                                                              : line.line}
                                                      </div>
                                                  ))}
                                        <div className="h-[40vh]" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </aside>

                    <aside
                        className={`
                        fixed lg:static top-[70px] right-0 bottom-24 w-[400px]
                        border-l border-white/10 
                        transform transition-transform duration-300 ease-in-out overflow-hidden
                        ${showLyrics ? "translate-x-0" : "translate-x-full"} lg:translate-x-0 
                        ${showLyrics ? "" : "lg:hidden"}
                        ${isLyricsExpanded ? "hidden" : ""}
                        bg-black
                        z-50
                    `}>
                        <div className="h-full flex flex-col">
                            <button
                                onClick={() => setIsLyricsExpanded(true)}
                                className="absolute top-4 right-4 z-10 text-white/60 hover:text-white transition-colors">
                                <Maximize className="w-5 h-5" />
                            </button>

                            <div className="relative h-[300px] w-full shrink-0">
                                {videoUrl ? (
                                    <video
                                        key={videoUrl}
                                        src={videoUrl}
                                        className="absolute inset-0 w-full h-full object-cover"
                                        autoPlay
                                        loop
                                        muted
                                        playsInline
                                    />
                                ) : (
                                    <img
                                        src={playerState.current?.thumbnail}
                                        alt=""
                                        className="absolute inset-0 w-full h-full object-cover"
                                    />
                                )}
                                <div className="absolute inset-0 bg-gradient-to-b from-black/20 to-black" />

                                <div className="absolute bottom-0 left-0 right-0 p-6">
                                    <h2 className="text-2xl font-bold text-white mb-2">
                                        {playerState.current?.title}
                                    </h2>
                                    <div>
                                        <button
                                            onClick={() => setShowArtistView(true)}
                                            className="text-white/60 hover:text-white transition-colors flex items-center gap-2">
                                            <span>{playerState.current?.artist}</span>
                                            {artistInfo?.artist && (
                                                <span className="text-sm text-white/40">
                                                    •{" "}
                                                    {artistInfo.artist.listeners.toLocaleString()}{" "}
                                                    monthly listeners
                                                </span>
                                            )}
                                        </button>
                                        {artistInfo?.artist && (
                                            <div className="flex flex-wrap gap-2 mt-2">
                                                {artistInfo.artist.tags
                                                    .slice(0, 3)
                                                    .map((tag: any) => (
                                                        <span
                                                            key={tag.name}
                                                            className="text-xs px-2 py-0.5 bg-white/10 rounded-full text-white/60">
                                                            {tag.name}
                                                        </span>
                                                    ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="relative flex-1 overflow-hidden">
                                <div className="absolute inset-0 overflow-y-auto lyrics-container">
                                    <div className="min-h-full">
                                        {lyrics?.results
                                            ?.find(result => result.lyrics?.length > 0)
                                            ?.lyrics?.map((line, index) => (
                                                <div
                                                    key={index}
                                                    ref={
                                                        isCurrentLine(index)
                                                            ? currentLineRef
                                                            : null
                                                    }
                                                    onClick={() =>
                                                        handleLyricSeek(line.milliseconds)
                                                    }
                                                    className={`
                                                    px-8 py-4 text-3xl leading-tight font-bold transition-colors duration-300 cursor-pointer
                                                    hover:text-white
                                                    ${isCurrentLine(index) ? "text-white" : isPastLine(index) ? "text-zinc-600" : "text-zinc-500"}
                                                `}>
                                                    {line.line.trim() === "" ? "♪" : line.line}
                                                </div>
                                            ))}
                                        <div className="h-[40vh]" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </aside>
                </div>

                <div className="fixed bottom-0 inset-x-0 h-24 bg-[#111111] border-t border-[#222222] z-[9999]">
                    <div className=" transition-all duration-200">
                        <div className="lg:hidden">
                            <div className="p-4 flex items-center justify-between">
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <div className="w-12 h-12 rounded overflow-hidden">
                                        <img
                                            src={playerState.current?.thumbnail}
                                            alt={playerState.current?.title}
                                            className="w-full h-full object-cover"
                                        />
                                    </div>
                                    <div className="min-w-0">
                                        <div className="text-white font-medium truncate text-sm">
                                            {playerState.current?.title}
                                        </div>
                                        <div className="text-white/60 text-xs truncate">
                                            {playerState.current?.artist}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={controls.togglePlay}
                                        className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
                                        {playerState.controls.isPlaying ? (
                                            <Pause className="w-4 h-4 text-black" />
                                        ) : (
                                            <Play className="w-4 h-4 text-black" />
                                        )}
                                    </button>
                                    <button
                                        onClick={() => setIsPlayerExpanded(!isPlayerExpanded)}>
                                        <ChevronUp className="w-5 h-5 text-white/60" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="hidden lg:block p-4">
                            <div className="mx-auto flex items-center justify-between px-6">
                                <div className="flex items-center gap-4 flex-1 min-w-0">
                                    <div className="w-14 h-14 rounded overflow-hidden">
                                        <img
                                            src={playerState.current?.thumbnail}
                                            alt={playerState.current?.title}
                                            className="w-full h-full object-cover"
                                        />
                                    </div>
                                    <div className="min-w-0">
                                        <div className="text-white font-medium truncate text-sm">
                                            {playerState.current?.title}
                                        </div>
                                        <div className="text-white/60 text-xs truncate">
                                            {playerState.current?.artist}
                                        </div>
                                    </div>
                                    <button className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                                        <Heart className="w-5 h-5 text-white/60" />
                                    </button>
                                </div>

                                <div className="flex flex-col items-center gap-2 flex-1">
                                    <div className="flex items-center gap-4">
                                        <button className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                                            <SkipBack className="w-5 h-5 text-white/60" />
                                        </button>
                                        <button
                                            onClick={controls.togglePlay}
                                            className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
                                            {playerState.controls.isPlaying ? (
                                                <Pause className="w-5 h-5 text-black" />
                                            ) : (
                                                <Play className="w-5 h-5 text-black" />
                                            )}
                                        </button>
                                        <button className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                                            <SkipForward className="w-5 h-5 text-white/60" />
                                        </button>
                                    </div>
                                    <div className="flex items-center gap-2 w-full max-w-md">
                                        <span className="text-xs text-white/60">
                                            {formatTime(currentTime)}
                                        </span>
                                        <div className="flex-1 h-1 bg-white/10 rounded-full">
                                            <div
                                                className="h-full bg-white rounded-full transition-all duration-300"
                                                style={{
                                                    width: `${(currentTime / (playerState.current?.duration || 1)) * 100}%`
                                                }}
                                            />
                                        </div>
                                        <span className="text-xs text-white/60">
                                            {formatTime(playerState.current?.duration)}
                                        </span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4 flex-1 justify-end">
                                    <button
                                        onClick={handleLyricsClick}
                                        className={`p-2 hover:bg-white/5 rounded-lg transition-colors ${showLyrics ? "text-evict-pink" : "text-white/60"}`}>
                                        <Mic2 className="w-5 h-5" />
                                    </button>
                                    <button
                                        onClick={handleQueueClick}
                                        className={`p-2 hover:bg-white/5 rounded-lg transition-colors ${showQueue ? "text-evict-pink" : "text-white/60"}`}>
                                        <ListMusic className="w-5 h-5" />
                                    </button>
                                    <button
                                        onClick={() => setShowFilters(!showFilters)}
                                        className={`p-2 hover:bg-white/5 rounded-lg transition-colors ${showFilters ? "text-evict-pink" : "text-white/60"}`}>
                                        <AudioWaveformIcon className="w-5 h-5" />
                                    </button>
                                    <Volume2 className="w-5 h-5 text-white/60" />
                                    <div className="w-24 h-1 bg-white/10 rounded-full">
                                        <div className="w-1/2 h-full bg-white rounded-full" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <QueueSection />
            </div>
        </MusicContext.Provider>
    )
}
