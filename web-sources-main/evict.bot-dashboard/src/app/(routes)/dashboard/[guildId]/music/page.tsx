// @ts-nocheck

"use client"

import { fetchGuildMusic } from "@/libs/dashboard/guild/music"
import { fetchVoiceInfo } from "@/libs/dashboard/guild/voice"
import ColorThief from "colorthief"
import {
    AudioWaveformIcon,
    ChevronDown,
    ChevronLeft,
    ChevronUp,
    Clock,
    Globe,
    GripVertical,
    Heart,
    ListMusic,
    Lock,
    Mic2,
    Pause,
    Play,
    Plus,
    RefreshCw,
    Repeat,
    Search,
    Settings,
    Shield,
    SkipBack,
    SkipForward,
    Users,
    Volume2,
    Waves,
    X
} from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState, memo } from "react"
import { useMusicContext } from "./music-context"
import { Swiper, SwiperSlide } from 'swiper/react'
import 'swiper/css'
import { Mousewheel } from 'swiper/modules'
import { useToken } from "@/hooks/useToken"

type LyricsResult = {
    results: [
        {
            lyrics: {
                line: string
                lrc_timestamp: string
                milliseconds: number
            }[]
            richSync:
                | {
                      startTime: number
                      endTime: number
                      text: string
                      words: { char: string; offset: number }[]
                  }[]
                | null
            author: string
            source: string
        }
    ]
}

const formatTime = (ms: number) => {
    if (!ms) return "--:--"
    const totalSeconds = Math.floor(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

interface MusicData {
    recently_played: {
        title: string
        uri: string
        author: string
        artwork_url: string
        playlist: {
            name: string
            url: string
        }
        played_at: string
    }[]
    playlists: {
        name: string
        url: string
        track_count: number
        tracks: {
            artwork_url: string
        }[]
    }[]
}

interface AudioFilters {
    bassboost: number
    nightcore: number
    reverb: number
}

interface VoiceState {
    voiceInfo: Awaited<ReturnType<typeof fetchVoiceInfo>> | null
    error: string | null
}

interface Track {
    title: string
    artist: string
    duration: number
    thumbnail: string
    uri: string
}

interface PlayerState {
    current: {
        title: string
        artist: string
        duration: number
        position: number
        thumbnail: string
        uri: string
        is_playing: boolean
    } | null
    queue: Track[]
    controls: {
        volume: number
        isPlaying: boolean
        repeat: "off" | "track" | "queue"
        shuffle: boolean
    }
}

interface Recommendation {
    title: string
    author: string
    artworkUrl: string
    duration: number
}

interface DiscoverTrack {
    title: string
    artist: string
    thumbnail: string
    videoUrl: string
    spotifyId: string
}

const SearchResults = ({ results }) => (
    <div className="space-y-6">
        <div>
            <h2 className="text-white text-lg font-bold">Artists</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {results.artists.map((artist, index) => (
                    <div key={index} className="flex flex-col items-center">
                        <img
                            src={artist.image || "/placeholder.jpg"}
                            alt={artist.name}
                            className="w-24 h-24 rounded-full"
                        />
                        <div className="text-white mt-2">{artist.name}</div>
                    </div>
                ))}
            </div>
        </div>

        <div>
            <h2 className="text-white text-lg font-bold">Songs</h2>
            <div className="space-y-2">
                {results.tracks.map((track, index) => (
                    <div key={index} className="flex items-center gap-3">
                        <img
                            src={track.image || "/placeholder.jpg"}
                            alt={track.name}
                            className="w-12 h-12 rounded"
                        />
                        <div>
                            <div className="text-white">{track.name}</div>
                            <div className="text-white/60 text-sm">{track.artist}</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    </div>
)

export default function MusicPage({ params }: { params: { guildId: string } }) {
    const wsRef = useRef<WebSocket | null>(null)
    const [isConnected, setIsConnected] = useState(false)
    const [isConnecting, setIsConnecting] = useState(false)
    const [connectionError, setConnectionError] = useState<string | null>(null)
    const token = useToken()
    const heartbeatRef = useRef<NodeJS.Timeout | null>(null)
    const mountedRef = useRef(true)
    const reconnectAttempts = useRef(0)
    const lastConnectionAttempt = useRef(0)
    const lastProcessedSong = useRef<string>("")
    const searchInputRef = useRef<HTMLInputElement>(null)
    const [searchResults, setSearchResults] = useState<{
        tracks: any[]
        artists: any[]
        albums: any[]
        playlists: any[]
    }>({ tracks: [], artists: [], albums: [], playlists: [] })
    const [isSearching, setIsSearching] = useState(false)
    const [searchQuery, setSearchQuery] = useState("")
    const searchTimeoutRef = useRef<NodeJS.Timeout>()

    const debouncedSearch = (query: string) => {
        setSearchQuery(query)

        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current)
        }

        searchTimeoutRef.current = setTimeout(() => {
            performSearch(query)
        }, 2000) 
    }

    const performSearch = async (query: string) => {
        if (!query.trim()) {
            setSearchResults({ tracks: [], artists: [], albums: [], playlists: [] })
            setIsSearching(false)
            return
        }

        setIsSearching(true)
        try {
            const response = await fetch(`/api/listen/search?query=${encodeURIComponent(query)}`)

            const formattedResults = {
                tracks: data.find((cat: any) => cat.category === "tracks")?.data || [],
                artists: data.find((cat: any) => cat.category === "artists")?.data || [],
                albums: data.find((cat: any) => cat.category === "albums")?.data || [],
                playlists: data.find((cat: any) => cat.category === "playlists")?.data || []
            }

            setSearchResults(formattedResults)
        } catch (error) {
            console.error("Search failed:", error)
        }
        setIsSearching(false)
    }

    const {
        setPlayerState,
        setLyrics,
        setCurrentTime,
        showArtistView,
        setShowArtistView,
        artistInfo,
        setArtistInfo
    } = useMusicContext()

    const sendMessage = (type: string, data: any = {}) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type, data }))
        }
    }

    const startHeartbeat = (interval: number) => {
        heartbeatRef.current = setInterval(() => {
            sendMessage("PING")
        }, interval)
    }

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

    const fetchDeezerThumbnail = async (title: string, artist: string): Promise<string | null> => {
        try {
            const [cleanTitle, cleanArtist] = cleanTitleForSearch(title, artist)
            const query = encodeURIComponent(`${cleanTitle} ${cleanArtist}`)

            console.log("🎵 Deezer Search:", {
                original: { title, artist },
                cleaned: { cleanTitle, cleanArtist },
                query
            })

            const response = await fetch(`/api/deezer/search?q=${query}`)
            const data = await response.json()

            if (data.data?.[0]?.album?.cover_big) {
                const thumbnailUrl = data.data[0].album.cover_big
                console.log("🎵 Found Deezer thumbnail:", thumbnailUrl)
                return thumbnailUrl
            }

            return null
        } catch (error) {
            console.error("🎵 Deezer fetch error:", error)
            return null
        }
    }

    const handleMessage = async (event: MessageEvent) => {
        try {
            const data = JSON.parse(event.data)
            console.log("🎵 Raw message received:", event.data)

            switch (data.type) {
                case "HELLO":
                    console.log("🎵 Received HELLO")
                    startHeartbeat(data.data.heartbeat_interval)
                    break

                case "STATE_UPDATE":
                    const state = data.data
                    console.log("🎵 Received state update:", state)

                    if (state.current) {
                        const songId = `${state.current.title}-${state.current.artist}`

                        if (songId !== lastProcessedSong.current) {
                            lastProcessedSong.current = songId
                            console.log("🎵 New song detected, fetching thumbnail...")

                            const defaultThumbnail = state.current.thumbnail

                            fetchDeezerThumbnail(state.current.title, state.current.artist).then(
                                deezerThumbnail => {
                                    if (!mountedRef.current) return

                                    setPlayerState(prevState => ({
                                        ...prevState,
                                        current: prevState.current
                                            ? {
                                                  ...prevState.current,
                                                  thumbnail: deezerThumbnail || defaultThumbnail
                                              }
                                            : null
                                    }))
                                }
                            )
                        }
                    }

                    if (mountedRef.current) {
                        setPlayerState(prevState => {
                            const newState = {
                                ...prevState,
                                ...state,
                                current: state.current
                                    ? {
                                          ...(prevState.current || {}),
                                          ...state.current,
                                          thumbnail: prevState.current?.thumbnail || state.current.thumbnail,
                                          position: state.current.position || 0,
                                          is_playing: state.current.is_playing
                                      }
                                    : null,
                                queue: state.queue || [],
                                controls: {
                                    ...prevState.controls,
                                    ...state.controls
                                }
                            }

                            console.log("🎵 Player state updated:", {
                                previous: prevState,
                                new: newState
                            })

                            return newState
                        })
                        setCurrentTime(state.current.position)
                    }
                    break

                case "ERROR":
                    console.error("🎵 WS Error:", data.data.message)
                    setConnectionError(data.data.message)
                    break
            }
        } catch (error) {
            console.error("🎵 Message handling error:", error)
        }
    }

    const cleanup = useCallback(() => {
        if (heartbeatRef.current) {
            clearInterval(heartbeatRef.current)
            heartbeatRef.current = null
        }
        if (wsRef.current) {
            try {
                const ws = wsRef.current
                ws.onclose = null
                ws.onerror = null
                ws.onmessage = null
                ws.onopen = null

                if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
                    ws.close()
                }

                wsRef.current = null
            } catch (error) {
                console.error("Cleanup error:", error)
            }
        }

        setIsConnected(false)
        setIsConnecting(false)
        setConnectionError(null)
    }, [])

    useEffect(() => {
        mountedRef.current = true

        if (!token || wsRef.current || isConnecting) return

        const maxRetries = 3
        const backoffDelay = 1000
        let attemptCount = 0
        let timeoutIds: NodeJS.Timeout[] = []

        const cleanup = () => {
            if (!mountedRef.current) return
            console.log("🎵 Cleaning up WebSocket connection...")

            timeoutIds.forEach(id => clearTimeout(id))
            timeoutIds = []

            if (heartbeatRef.current) {
                clearInterval(heartbeatRef.current)
                heartbeatRef.current = null
            }

            if (wsRef.current) {
                const ws = wsRef.current
                ws.onclose = null
                ws.onerror = null
                ws.onmessage = null
                ws.onopen = null
                wsRef.current = null
            }
        }

        const connect = () => {
            if (!mountedRef.current) return

            console.log("🎵 Initiating connection...")
            setIsConnecting(true)

            const ws = new WebSocket(`wss://api.evict.bot/ws/music/${params.guildId}?auth=${token}`)
            wsRef.current = ws

            ws.onmessage = handleMessage

            ws.onopen = () => {
                if (!mountedRef.current) return
                console.log("🎵 WebSocket connected successfully")
                setIsConnected(true)
                setIsConnecting(false)
                sendMessage("HELLO")
            }

            ws.onclose = event => {
                if (!mountedRef.current) return
                console.log("🎵 WebSocket closed:", event.code, event.reason)

                if (event.code !== 1000 && attemptCount < maxRetries) {
                    attemptCount++
                    const delay = backoffDelay * Math.pow(2, attemptCount)
                    console.log(
                        `🎵 Reconnecting in ${delay}ms (attempt ${attemptCount}/${maxRetries})`
                    )
                    const retryTimeout = setTimeout(connect, delay)
                    timeoutIds.push(retryTimeout)
                }

                cleanup()
            }

            ws.onerror = error => {
                if (!mountedRef.current) return
                console.error("🎵 WebSocket error:", error)
            }
        }

        connect()

        return () => {
            mountedRef.current = false
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.close(1000, "Component unmounting")
            }
            cleanup()
        }
    }, [params.guildId, token])

    const { playerState, lyrics, currentTime } = useMusicContext()

    const [mounted, setMounted] = useState(false)
    const [isSearchFocused, setIsSearchFocused] = useState(false)
    const [isPlayerExpanded, setIsPlayerExpanded] = useState(false)
    const [showLyrics, setShowLyrics] = useState(false)
    const [lyricsLoading, setLyricsLoading] = useState(false)
    const [dominantColor, setDominantColor] = useState<[number, number, number] | null>(null)
    const [palette, setPalette] = useState<[number, number, number][]>([])
    const [musicData, setMusicData] = useState<MusicData | null>(null)
    const [filters, setFilters] = useState<AudioFilters>({
        bassboost: 0,
        nightcore: 0,
        reverb: 0
    })
    const [showFilters, setShowFilters] = useState(false)
    const [currentView, setCurrentView] = useState<"home" | "playlist">("home")
    const [selectedPlaylist, setSelectedPlaylist] = useState<any>(null)
    const [voiceState, setVoiceState] = useState<VoiceState>({
        voiceInfo: null,
        error: null
    })
    const [playlistDominantColor, setPlaylistDominantColor] = useState<
        [number, number, number] | null
    >(null)
    const [showSettings, setShowSettings] = useState(false)
    const [showSettingsModal, setShowSettingsModal] = useState(false)
    const [activeTab, setActiveTab] = useState<"all" | "playlists" | "recent">("all")
    const [isSearchExpanded, setIsSearchExpanded] = useState(false)
    const [playlistFilter, setPlaylistFilter] = useState("")
    const [playlistSort, setPlaylistSort] = useState<
        "custom" | "title" | "artist" | "album" | "date_added" | "duration"
    >("custom")
    const [originalTracks, setOriginalTracks] = useState<any[]>([])
    const [showAllRecent, setShowAllRecent] = useState(false)
    const [showAllPlaylists, setShowAllPlaylists] = useState(false)
    const [recommendations, setRecommendations] = useState<Recommendation[]>([])
    const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false)
    const [showQueue, setShowQueue] = useState(false)
    const [currentTrackId, setCurrentTrackId] = useState<string | null>(null)
    const [trackInfo, setTrackInfo] = useState<any>(null)
    const [audioUrl, setAudioUrl] = useState<string | null>(null)

    const [failedImages, setFailedImages] = useState<Set<string>>(new Set())

    const [discoverTracks, setDiscoverTracks] = useState<DiscoverTrack[]>([])
    const [isLoadingDiscover, setIsLoadingDiscover] = useState(false)
    const [currentDiscoverIndex, setCurrentDiscoverIndex] = useState(0)

    const handleImageError = (url: string) => {
        setFailedImages(prev => new Set(prev).add(url))
    }

    useEffect(() => {
        if (selectedPlaylist?.tracks) {
            setOriginalTracks([...selectedPlaylist.tracks])
        }
    }, [selectedPlaylist])

    useEffect(() => {
        const fetchLyrics = async () => {
            if (!playerState.current?.title || !showLyrics) return

            setLyricsLoading(true)
            try {
                const [cleanTitle, cleanArtist] = cleanTitleForSearch(
                    playerState.current.title,
                    playerState.current.artist
                )

                const response = await fetch(`/api/listen/lyrics?title=${encodeURIComponent(cleanTitle)}&artist=${encodeURIComponent(cleanArtist)}`)
                if (!response.ok) throw new Error("Failed to fetch lyrics")
                const data = await response.json()
                setLyrics(data)
            } catch (error) {
                console.error("Error fetching lyrics:", error)
                setLyrics(null)
            } finally {
                setLyricsLoading(false)
            }
        }

        fetchLyrics()
    }, [showLyrics, playerState.current?.title, playerState.current?.artist])

    const recentSearches = [
        { id: 1, title: "Sad songs for tik tok edits", artist: "GABRIELE" },
        { id: 2, title: "Sad playlist to cry to at 3am 🌊", artist: "RP" },
        { id: 3, title: "Sad Late Night Mix", artist: "Spotify" },
        {
            id: 4,
            title: "The Line (from the series Arcane League of...",
            artist: "Twenty One Pilots, Arcane, League of Legends"
        },
        { id: 5, title: "The Line", artist: "Arcane" }
    ]

    const currentLineRef = useRef<HTMLDivElement>(null)
    const lyricsContainerRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const searchContainer = document.querySelector(".search-container")
            if (searchContainer && !searchContainer.contains(event.target as Node)) {
                setIsSearchFocused(false)
            }
        }

        if (isSearchFocused) {
            document.addEventListener("mousedown", handleClickOutside)
            return () => document.removeEventListener("mousedown", handleClickOutside)
        }
    }, [isSearchFocused])

    useEffect(() => {
        const loadColors = async () => {
            if (!playerState.current?.thumbnail) {
                console.log("No thumbnail for color extraction")
                return
            }

            try {
                const img = new Image()
                img.crossOrigin = "Anonymous"
                img.onload = () => {
                    try {
                        const colorThief = new ColorThief()
                        const colors = colorThief.getPalette(img, 3)
                        console.log("Extracted colors:", colors)
                        setDominantColor(colors[0])
                        setPalette(colors)
                    } catch (error) {
                        console.error("Color extraction error:", error)
                        setDominantColor([45, 45, 45])
                        setPalette([
                            [45, 45, 45],
                            [35, 35, 35],
                            [25, 25, 25]
                        ])
                    }
                }
                img.src = playerState.current.thumbnail
            } catch (error) {
                console.error("Color loading error:", error)
                setDominantColor([45, 45, 45])
                setPalette([
                    [45, 45, 45],
                    [35, 35, 35],
                    [25, 25, 25]
                ])
            }
        }

        loadColors()
    }, [playerState.current?.thumbnail])

    useEffect(() => {
        const loadPlaylistColors = async () => {
            if (!selectedPlaylist?.tracks?.[0]?.artwork_url) {
                console.log("No playlist artwork for color extraction")
                return
            }

            try {
                const img = new Image()
                img.crossOrigin = "Anonymous"
                img.onload = () => {
                    try {
                        const colorThief = new ColorThief()
                        const colors = colorThief.getPalette(img, 3)
                        console.log("Extracted playlist colors:", colors)
                        setPlaylistDominantColor(colors[0])
                    } catch (error) {
                        console.error("Playlist color extraction error:", error)
                        setPlaylistDominantColor([45, 45, 45])
                    }
                }
                img.src = selectedPlaylist.tracks[0].artwork_url
            } catch (error) {
                console.error("Playlist color loading error:", error)
                setPlaylistDominantColor([45, 45, 45])
            }
        }

        loadPlaylistColors()
    }, [selectedPlaylist?.tracks])

    useEffect(() => {
        if (!playerState.current?.is_playing) return

        if (currentTime >= playerState.current.duration) return

        setCurrentTime(playerState.current.position)

        const interval = setInterval(() => {
            setCurrentTime(prev => {
                if (prev >= (playerState.current?.duration ?? 0)) {
                    clearInterval(interval)
                    return playerState.current?.duration ?? 0
                }
                return prev + 1000
            })
        }, 1000)

        return () => clearInterval(interval)
    }, [
        playerState.current?.is_playing,
        playerState.current?.position,
        playerState.current?.duration
    ])

    useEffect(() => {
        if (playerState.current) {
            setCurrentTime(playerState.current.position)
        }
    }, [playerState.current?.title])

    useEffect(() => {
        if (currentLineRef.current && lyricsContainerRef.current) {
            currentLineRef.current.scrollIntoView({
                behavior: "smooth",
                block: "center"
            })
        }
    }, [currentTime])

    useEffect(() => {
        const fetchMusic = async () => {
            try {
                const data = await fetchGuildMusic(params.guildId)
                setMusicData(data)
            } catch (error) {
                console.error("Error fetching music:", error)
            }
        }

        fetchMusic()
    }, [params.guildId])
    useEffect(() => {
        const fetchVoice = async () => {
            try {
                const data = await fetchVoiceInfo(params.guildId)
                setVoiceState({ voiceInfo: data, error: null })
            } catch (error) {
                setVoiceState(prev => ({
                    ...prev,
                    error: error instanceof Error ? error.message : "Failed to fetch voice info"
                }))
            }
        }

        fetchVoice()
        const interval = setInterval(fetchVoice, 5000)
        return () => clearInterval(interval)
    }, [params.guildId])

    const fetchRecommendations = async () => {
        if (!playerState.current?.title) return

        setIsLoadingRecommendations(true)
        try {
            const response = await fetch(`/api/listen/autoplay?title=${encodeURIComponent(playerState.current.title)}&author=${encodeURIComponent(playerState.current.artist)}`)
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

    const controls = {
        play: () => sendMessage("PLAY"),
        pause: () => sendMessage("PAUSE"),
        skip: () => sendMessage("SKIP"),
        seek: (position: number) => sendMessage("SEEK", { position }),
        setVolume: (volume: number) => sendMessage("VOLUME", { volume }),
        toggleShuffle: () => sendMessage("SHUFFLE"),
        setRepeat: (mode: "track" | "queue" | "off") => sendMessage("REPEAT", { mode }),
        togglePlay: () => sendMessage(playerState.controls.isPlaying ? "PAUSE" : "PLAY")
    }

    const bgGradient = dominantColor
        ? `linear-gradient(to bottom, rgba(${dominantColor.join(",")}, 0.3), rgba(${dominantColor.join(",")}, 0))`
        : "none"

    const ExpandedMobilePlayer = () => (
        <div
            className={`fixed inset-0 bg-black z-50 transition-transform duration-300 
            ${isPlayerExpanded ? "translate-y-0" : "translate-y-full"}`}>
            <div className="h-full flex flex-col p-6">
                <div className="flex items-center justify-between mb-8">
                    <button onClick={() => setIsPlayerExpanded(false)}>
                        <ChevronDown className="w-6 h-6 text-white/60" />
                    </button>
                    <span className="text-white/60 text-sm">Now Playing</span>
                    <div className="w-6" />
                </div>

                {playerState.current && (
                    <div className="flex-1 flex flex-col items-center justify-center space-y-6">
                        <div className="w-64 h-64 rounded-lg overflow-hidden shadow-2xl">
                            <img
                                src={playerState.current.thumbnail}
                                alt={playerState.current.title}
                                className="w-full h-full object-cover"
                            />
                        </div>

                        <div className="text-center">
                            <h2 className="text-white text-xl font-bold mb-2">
                                {playerState.current.title}
                            </h2>
                            <p className="text-white/60">{playerState.current.artist}</p>
                        </div>

                        <div className="w-full max-w-md space-y-4">
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-white/60">
                                    {formatTime(playerState.current.position)}
                                </span>
                                <div className="flex-1 h-1 bg-white/10 rounded-full">
                                    <div
                                        className="h-full bg-white rounded-full transition-all duration-300"
                                        style={{
                                            width: `${(playerState.current.position / playerState.current.duration) * 100}%`
                                        }}
                                    />
                                </div>
                                <span className="text-xs text-white/60">
                                    {formatTime(playerState.current.duration)}
                                </span>
                            </div>

                            <div className="flex items-center justify-center gap-8">
                                <button
                                    className="p-2">
                                    <SkipBack className="w-6 h-6 text-white/60" />
                                </button>
                                <button
                                    onClick={controls.togglePlay}
                                    className="w-14 h-14 bg-white rounded-full flex items-center justify-center">
                                    {playerState.controls.isPlaying ? (
                                        <Pause className="w-7 h-7 text-black" />
                                    ) : (
                                        <Play className="w-7 h-7 text-black" />
                                    )}
                                </button>
                                <button onClick={controls.skip} className="p-2">
                                    <SkipForward className="w-6 h-6 text-white/60" />
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )

    const uniqueRecentlyPlayed = musicData?.recently_played.filter(
        (track, index, self) => index === self.findIndex(t => t.title === track.title)
    )

    const SettingsMenu = () => (
        <div
            className={`
            absolute top-12 right-4 w-48 bg-[#111111] border border-white/10 
            rounded-lg shadow-lg z-50 py-1 ${showSettings ? "block" : "hidden"}
        `}>
            <div className="px-3 py-2 text-xs text-white/40 font-medium">VOICE SETTINGS</div>
            <button className="w-full px-3 py-2 text-sm text-white/60 hover:bg-white/5 text-left flex items-center gap-2">
                <Volume2 className="w-4 h-4" />
                Volume
            </button>
            <button className="w-full px-3 py-2 text-sm text-white/60 hover:bg-white/5 text-left flex items-center gap-2">
                <Users className="w-4 h-4" />
                User Limit
            </button>
            <button className="w-full px-3 py-2 text-sm text-white/60 hover:bg-white/5 text-left flex items-center gap-2">
                <Lock className="w-4 h-4" />
                Make Private
            </button>
        </div>
    )

    const SettingsModal = () => (
        <div
            className={`
            fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4
            ${showSettingsModal ? "block" : "hidden"}
        `}>
            <div className="bg-[#111111] w-full max-w-lg rounded-lg p-4 md:p-6 space-y-4 md:space-y-6 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between sticky top-0 bg-[#111111] py-2">
                    <h3 className="text-white text-lg font-medium">Room Settings</h3>
                    <button
                        onClick={() => setShowSettingsModal(false)}
                        className="text-white/60 hover:text-white">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="space-y-4 md:space-y-6">
                    <div className="space-y-2">
                        <label className="text-white font-medium">Room Name</label>
                        <input
                            type="text"
                            value="adam's channel"
                            className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-3 py-2 text-white"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-white font-medium flex items-center gap-2">
                            Room Visibility
                            <span className="text-sm text-white/40">(who can join)</span>
                        </label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <button className="w-full flex flex-col gap-2 p-4 rounded-lg bg-[#0a0a0a] border border-white/10 hover:bg-white/5">
                                <div className="flex items-center gap-2">
                                    <Globe className="w-4 h-4 text-white/60" />
                                    <span className="text-white font-medium">Open</span>
                                </div>
                                <span className="text-sm text-white/60">
                                    Anyone can join your room at any time.
                                </span>
                            </button>
                            <button className="w-full flex flex-col gap-2 p-4 rounded-lg bg-evict-pink/20 border border-evict-pink">
                                <div className="flex items-center gap-2">
                                    <Users className="w-4 h-4 text-evict-pink" />
                                    <span className="text-white font-medium">Friends</span>
                                </div>
                                <span className="text-sm text-white/60">
                                    Only your friends can join your room.
                                </span>
                            </button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-white font-medium">Room Control</label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <button className="flex flex-col gap-2 p-3 rounded-lg bg-evict-pink/20 border border-evict-pink">
                                <div className="flex items-center gap-2">
                                    <Shield className="w-4 h-4 text-evict-pink" />
                                    <span className="text-white font-medium">Hosts</span>
                                </div>
                                <span className="text-sm text-white/60">
                                    Only selected hosts can control the music.
                                </span>
                            </button>
                            <button className="flex flex-col gap-2 p-3 rounded-lg bg-[#0a0a0a] border border-white/10 hover:bg-white/5">
                                <div className="flex items-center gap-2">
                                    <Users className="w-4 h-4 text-white/60" />
                                    <span className="text-white font-medium">Everyone</span>
                                </div>
                                <span className="text-sm text-white/60">
                                    Anyone can control the music.
                                </span>
                            </button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-white font-medium">Queue Mode</label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <button className="flex flex-col gap-2 p-3 rounded-lg bg-[#0a0a0a] border border-white/10 hover:bg-white/5">
                                <div className="flex items-center gap-2">
                                    <Repeat className="w-4 h-4 text-white/60" />
                                    <span className="text-white font-medium">Loop</span>
                                </div>
                                <span className="text-sm text-white/60">
                                    Queue will repeat when finished.
                                </span>
                            </button>
                            <button className="flex flex-col gap-2 p-3 rounded-lg bg-evict-pink/20 border border-evict-pink">
                                <div className="flex items-center gap-2">
                                    <ListMusic className="w-4 h-4 text-evict-pink" />
                                    <span className="text-white font-medium">Standard</span>
                                </div>
                                <span className="text-sm text-white/60">
                                    Queue will stop when finished.
                                </span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )

    const NowPlayingSkeleton = () => (
        <div className="flex items-center gap-4 animate-pulse">
            <div className="w-14 h-14 bg-white/5 rounded-lg"></div>
            <div className="flex-1 space-y-2">
                <div className="h-4 bg-white/5 rounded w-48"></div>
                <div className="h-3 bg-white/5 rounded w-32"></div>
            </div>
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/5 rounded-full"></div>
                <div className="w-5 h-5 bg-white/5 rounded"></div>
            </div>
        </div>
    )

    const sortTracks = (tracks: any[]) => {
        if (!tracks) return []

        switch (playlistSort) {
            case "title":
                return [...tracks].sort((a, b) => a.title.localeCompare(b.title))
            case "artist":
                return [...tracks].sort((a, b) => a.author.localeCompare(b.author))
            case "album":
                return [...tracks].sort((a, b) => (a.album || "").localeCompare(b.album || ""))
            case "date_added":
                return [...tracks].sort((a, b) => (b.added_at || 0) - (a.added_at || 0))
            case "duration":
                return [...tracks].sort((a, b) => (a.duration || 0) - (b.duration || 0))
            case "custom":
                return originalTracks
            default:
                return tracks
        }
    }

    const filterTracks = (tracks: any[]) => {
        if (!tracks) return []
        if (!playlistFilter) return tracks

        const searchTerm = playlistFilter.toLowerCase()
        return tracks.filter(
            track =>
                track.title.toLowerCase().includes(searchTerm) ||
                track.author.toLowerCase().includes(searchTerm) ||
                (track.album || "").toLowerCase().includes(searchTerm)
        )
    }

    const filteredAndSortedTracks = useMemo(() => {
        if (!selectedPlaylist?.tracks) {
            console.log("No tracks found in selected playlist")
            return []
        }

        const sorted = sortTracks(selectedPlaylist.tracks)
        const filtered = filterTracks(sorted)

        console.log("Tracks processing:", {
            originalCount: selectedPlaylist.tracks.length,
            sortedCount: sorted.length,
            filteredCount: filtered.length,
            firstTrack: filtered[0]
        })

        return filtered
    }, [selectedPlaylist?.tracks, playlistFilter, playlistSort, originalTracks])

    const fetchDiscoverContent = async () => {
        setIsLoadingDiscover(true)
        setDiscoverTracks([]) 

        try {
            console.log("Fetching discover content...")
            const response = await fetch(`/api/listen/autoplay?title=${encodeURIComponent(title)}&author=${encodeURIComponent(author)}`)
            const recommendations = await response.json()
            console.log("Got recommendations:", recommendations)

            const tracksWithVideos = await Promise.all(
                (Array.isArray(recommendations) ? recommendations : []).map(async (track: any) => {
                    try {
                        console.log("Processing track:", track.title)
                        const trackResponse = await fetch(
                            `/api/song?title=${encodeURIComponent(track.title)}&artist=${encodeURIComponent(track.author)}`
                        )
                        const trackData = await trackResponse.json()
                        console.log("Track data:", trackData)

                        if (trackData.spotify?.trackId) {
                            const videoResponse = await fetch(`/api/listen/video?spotifyId=${trackData.spotify.trackId}`)
                            const videoData = await videoResponse.json()
                            console.log("Video data:", videoData)

                            if (videoData.url) {
                                return {
                                    title: track.title,
                                    artist: track.author,
                                    thumbnail: track.artworkUrl,
                                    videoUrl: videoData.url,
                                    spotifyId: trackData.spotify.trackId
                                }
                            }
                        }
                        return null
                    } catch (error) {
                        console.error("Error processing track:", error)
                        return null
                    }
                })
            )

            const validTracks = tracksWithVideos.filter(Boolean)
            console.log("Final discover tracks:", validTracks)
            
            setDiscoverTracks(validTracks)
        } catch (error) {
            console.error("Failed to fetch discover content:", error)
        } finally {
            setIsLoadingDiscover(false)
        }
    }

    useEffect(() => {
        fetchDiscoverContent()
    }, [])

    useEffect(() => {
        if (activeTab === "discover") {
            console.log("Discover tab selected, fetching content...")
            fetchDiscoverContent()
        }
    }, [activeTab])

    useEffect(() => {
        if (activeTab === "discover") {
            fetchDiscoverContent()
        }
    }, [])

    const DiscoverSection = memo(function DiscoverSection() {
        if (isLoadingDiscover) {
            return (
                <div className="h-[calc(100vh-180px)] flex items-center justify-center">
                    <div className="flex items-center gap-3 text-white/60">
                        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                            <circle 
                                className="opacity-25" 
                                cx="12" 
                                cy="12" 
                                r="10" 
                                stroke="currentColor" 
                                strokeWidth="4"
                                fill="none"
                            />
                            <path 
                                className="opacity-75" 
                                fill="currentColor" 
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            />
                        </svg>
                        Loading discover content...
                    </div>
                </div>
            )
        }

        if (!discoverTracks || discoverTracks.length === 0) {
            return (
                <div className="h-[calc(100vh-180px)] flex items-center justify-center">
                    <div className="text-white/60">No discover content available</div>
                </div>
            )
        }

        return (
            <div className="h-[calc(100vh-180px)] flex justify-center">
                <div className="w-[calc((100vh-180px)*0.5625)] relative">
                    <Swiper
                        modules={[Mousewheel]}
                        direction="vertical"
                        className="h-full w-full"
                        onSlideChange={(swiper) => setCurrentDiscoverIndex(swiper.activeIndex)}
                        mousewheel={{
                            forceToAxis: true,
                            sensitivity: 1,
                            thresholdDelta: 50,
                            thresholdTime: 500,
                            releaseOnEdges: false,
                            invert: false
                        }}
                        resistance={true}
                        resistanceRatio={0}
                        speed={400}
                        spaceBetween={0}
                        slidesPerView={1}
                        preventInteractionOnTransition={true}
                        touchReleaseOnEdges={false}
                        cssMode={false}
                        noSwiping={true}
                        noSwipingClass="swiper-no-swiping"
                        >
                        {discoverTracks.map((track, index) => (
                            <SwiperSlide key={track.spotifyId} className="swiper-no-swiping">
                                <div className="relative h-full w-full">
                                    <video
                                        key={track.videoUrl}
                                        src={track.videoUrl}
                                        className="h-full w-full object-cover"
                                        autoPlay={currentDiscoverIndex === index}
                                        loop
                                        playsInline
                                        muted
                                        controls={false}
                                        onError={(e) => console.error("Video error:", e)}
                                    />
                                    <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/80 to-transparent">
                                        <h3 className="text-white text-xl font-bold mb-1">
                                            {track.title}
                                        </h3>
                                        <p className="text-white/80">{track.artist}</p>
                                        <button 
                                            onClick={() => {}}
                                            className="mt-4 bg-evict-pink text-white px-6 py-2 rounded-full font-medium hover:bg-evict-pink/90 transition-colors">
                                            Play Now
                                        </button>
                                    </div>
                                </div>
                            </SwiperSlide>
                        ))}
                    </Swiper>
                </div>
            </div>
        )
    }, (prevProps, nextProps) => true)

    const renderContent = () => {
        if (showArtistView && artistInfo?.artist) {
            return (
                <div className="px-6 py-8 max-w-6xl mx-auto">
                    <button
                        onClick={() => setShowArtistView(false)}
                        className="flex items-center gap-2 text-white/60 hover:text-white mb-8 transition-colors">
                        <ChevronLeft className="w-5 h-5" />
                        <span>Back</span>
                    </button>

                    <h1 className="text-5xl font-bold text-white mb-6">{artistInfo.artist.name}</h1>

                    <div className="flex flex-wrap gap-3 mb-8">
                        {artistInfo.artist.tags.map((tag: any) => (
                            <span
                                key={tag.name}
                                className="px-3 py-1 bg-white/10 rounded-full text-white/60 text-sm">
                                {tag.name}
                            </span>
                        ))}
                        <span className="text-white/40 text-sm">
                            {artistInfo.artist.listeners.toLocaleString()} monthly listeners
                        </span>
                    </div>

                    <div className="mb-12">
                        <h2 className="text-2xl font-bold text-white mb-4">About</h2>
                        <p className="text-white/80 leading-relaxed max-w-3xl">
                            {artistInfo.artist.bio.split("<a")[0]}
                        </p>
                    </div>

                    <div>
                        <h2 className="text-2xl font-bold text-white mb-6">Fans Also Like</h2>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
                            {artistInfo.artist.similar.map((artist: any) => (
                                <div key={artist.name} className="group">
                                    <div className="aspect-square mb-3 rounded-full overflow-hidden bg-white/5">
                                        {artist.image &&
                                        !failedImages.has(artist.image["#text"]) ? (
                                            <img
                                                src={artist.image["#text"]}
                                                alt={artist.name}
                                                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                                onError={() =>
                                                    handleImageError(artist.image["#text"])
                                                }
                                            />
                                        ) : (
                                            <div className="w-full h-full animate-pulse bg-white/10 rounded-full" />
                                        )}
                                    </div>
                                    <div className="text-sm font-medium text-white text-center">
                                        {artist.name}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )
        }

        switch (activeTab) {
            case "playlists":
                return (
                    <div
                        className={`flex-1 space-y-4 transition-all duration-200 pb-24 ${showLyrics ? "mr-[400px]" : ""}`}>
                        <div className={`flex-1 space-y-6 transition-all duration-200 pb-24`}>
                            <div className="px-6 mb-6 flex items-center gap-3 -mt-3">
                                <div
                                    className={`
                    flex items-center gap-2 bg-white/10 rounded-full h-12
                    ${isSearchExpanded ? "w-[300px]" : "w-12"} transition-all duration-300
                `}
                                    onMouseDown={e => e.stopPropagation()}>
                                    <button
                                        onClick={() => {
                                            setIsSearchExpanded(!isSearchExpanded)
                                            if (!isSearchExpanded) {
                                                setTimeout(
                                                    () => searchInputRef.current?.focus(),
                                                    100
                                                )
                                            }
                                        }}
                                        className="p-3 h-full aspect-square">
                                        <Search className="w-5 h-5 text-white" />
                                    </button>
                                    <input
                                        ref={searchInputRef}
                                        type="text"
                                        value={searchQuery}
                                        placeholder="Search..."
                                        onChange={e => debouncedSearch(e.target.value)}
                                        onKeyDown={e => {
                                            if (e.key === "Enter") {
                                                if (searchTimeoutRef.current) {
                                                    clearTimeout(searchTimeoutRef.current)
                                                }
                                                performSearch(e.target.value)
                                            }
                                        }}
                                        className={`
                        bg-transparent text-white outline-none border-none
                        ${isSearchExpanded ? "w-full pr-4" : "w-0 opacity-0"}
                        transition-all duration-300
                    `}
                                    />
                                </div>
                            </div>

                            <button
                                onClick={() =>
                                    setActiveTab(activeTab === "playlists" ? "all" : "playlists")
                                }
                                className={`
                                    px-6 py-3 rounded-full text-sm font-medium transition-all
                                    ${
                                        activeTab === "playlists"
                                            ? "bg-white text-black"
                                            : "bg-white/10 text-white hover:bg-white/20"
                                    }
                                `}>
                                Playlists
                            </button>

                            <button
                                onClick={() =>
                                    setActiveTab(activeTab === "recent" ? "all" : "recent")
                                }
                                className={`
                                    px-6 py-3 rounded-full text-sm font-medium transition-all
                                    ${
                                        activeTab === "recent"
                                            ? "bg-white text-black"
                                            : "bg-white/10 text-white hover:bg-white/20"
                                    }
                                `}>
                                Recently Played
                            </button>

                            {/* <button
                                onClick={() =>
                                    setActiveTab(activeTab === "discover" ? "all" : "discover")
                                }
                                className={`
                                    px-6 py-3 rounded-full text-sm font-medium transition-all
                                    ${
                                        activeTab === "discover"
                                            ? "bg-white text-black"
                                            : "bg-white/10 text-white hover:bg-white/20"
                                    }
                                `}>
                                Discover
                            </button> */}
                        </div>

                        <div className="px-6 space-y-4">
                            <div className="flex flex-wrap items-center gap-3">
                                <button className="bg-evict-pink hover:bg-evict-pink/90 text-white px-6 py-2.5 rounded-full font-medium transition-all hover:scale-105 flex items-center gap-2 text-sm">
                                    <Play className="w-4 h-4" fill="currentColor" />
                                    Play
                                </button>
                                <button className="bg-white/10 hover:bg-white/15 text-white px-6 py-2.5 rounded-full font-medium transition-all hover:scale-105 flex items-center gap-2 text-sm">
                                    <svg
                                        width="16"
                                        height="16"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2">
                                        <path d="M16 3 L21 8 L16 13" />
                                        <path d="M4 20 L21 20 L21 8" />
                                        <path d="M4 8 L9 3 L14 8" />
                                        <path d="M4 16 L4 4" />
                                    </svg>
                                    Shuffle
                                </button>
                            </div>

                            <div className="flex flex-col md:flex-row items-stretch md:items-center gap-4">
                                <div className="relative flex-1 max-w-full md:max-w-md">
                                    <input
                                        ref={searchInputRef}
                                        type="text"
                                        value={playlistFilter}
                                        onChange={e => setPlaylistFilter(e.target.value)}
                                        onFocus={() => setIsSearchFocused(true)}
                                        onBlur={() => setIsSearchFocused(false)}
                                        onClick={() => searchInputRef.current?.focus()}
                                        placeholder="Filter playlist"
                                        className={`
                                            w-full bg-white/5 border rounded-full px-4 py-2 text-sm text-white 
                                            placeholder:text-white/40 focus:outline-none transition-colors
                                            ${isSearchFocused ? "border-white/20" : "border-white/10"}
                                        `}
                                    />
                                    <button
                                        onClick={() => searchInputRef.current?.focus()}
                                        className="absolute right-4 top-1/2 -translate-y-1/2">
                                        <Search
                                            className={`
                                            w-4 h-4 transition-colors
                                            ${isSearchFocused ? "text-white/60" : "text-white/40"}
                                        `}
                                        />
                                    </button>
                                </div>
                                <select
                                    value={playlistSort}
                                    onChange={e =>
                                        setPlaylistSort(e.target.value as typeof playlistSort)
                                    }
                                    className="w-full md:w-auto bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white 
                                        appearance-none cursor-pointer hover:bg-white/10 transition-colors focus:border-white/20 focus:outline-none">
                                    <option value="custom">Custom order</option>
                                    <option value="title">Title</option>
                                    <option value="artist">Artist</option>
                                    <option value="album">Album</option>
                                    <option value="date_added">Date added</option>
                                    <option value="duration">Duration</option>
                                </select>
                            </div>
                        </div>

                        <div className="px-6">
                            <div className="border-b border-white/10 pb-2 mb-2">
                                <div className="grid grid-cols-[16px_4fr_3fr_minmax(120px,1fr)] gap-4 text-xs text-white/40 px-4">
                                    <div>#</div>
                                    <div>Title</div>
                                    <div>Album</div>
                                    <div className="flex justify-end">
                                        <Clock className="w-3.5 h-3.5" />
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-1">
                                {selectedPlaylist?.tracks ? (
                                    filteredAndSortedTracks.map((track: any, i: number) => (
                                        <div
                                            key={i}
                                            className="grid grid-cols-[16px_4fr_3fr_minmax(120px,1fr)] gap-4 p-2 rounded-lg hover:bg-white/5 group transition-colors cursor-pointer">
                                            <div className="text-white/40 text-sm self-center">
                                                {i + 1}
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <img
                                                    src={track.artwork_url}
                                                    alt=""
                                                    className="w-10 h-10 rounded"
                                                />
                                                <div>
                                                    <div className="text-white text-sm font-medium">
                                                        {track.title}
                                                    </div>
                                                    <div className="text-sm text-white/60">
                                                        {track.author}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="hidden md:block text-white/60 text-sm self-center">
                                                {track.album}
                                            </div>
                                            <div className="hidden md:block text-white/60 text-sm text-right self-center">
                                                {formatTime(track.duration)}
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center py-8 text-white/40">
                                        Loading playlist...
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )

            case "recent":
                return (
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-white">Recently Played</h3>
                            <button
                                onClick={() => setShowAllRecent(!showAllRecent)}
                                className="text-sm text-white/60 hover:text-white transition-colors">
                                {showAllRecent ? "Show less" : "Show all"}
                            </button>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                            {uniqueRecentlyPlayed
                                ?.slice(0, showAllRecent ? undefined : 8)
                                .map((track, i) => (
                                    <div
                                        key={i}
                                        className="bg-[#111111] rounded-lg p-3 hover:bg-[#222222] transition-colors group cursor-pointer">
                                        <div className="aspect-square rounded-lg relative mb-3 overflow-hidden">
                                            {track.artwork_url &&
                                            !failedImages.has(track.artwork_url) ? (
                                                <img
                                                    src={track.artwork_url}
                                                    alt={track.title}
                                                    className="w-full h-full object-cover"
                                                    loading="lazy"
                                                    decoding="async"
                                                    onError={() =>
                                                        handleImageError(track.artwork_url)
                                                    }
                                                />
                                            ) : (
                                                <div className="w-full h-full animate-pulse bg-white/10" />
                                            )}
                                            <div className="absolute bottom-2 right-2 w-8 h-8 bg-evict-pink rounded-full items-center justify-center hidden group-hover:flex shadow-lg translate-y-2 group-hover:translate-y-0 transition-all">
                                                <Play className="w-4 h-4 text-white" />
                                            </div>
                                        </div>
                                        <div className="text-white font-medium truncate text-sm mb-1">
                                            {track.title}
                                        </div>
                                        <div className="text-white/60 text-xs truncate">
                                            {track.author}
                                        </div>
                                    </div>
                                ))}
                        </div>
                    </section>
                )

            default:
                return (
                    <>
                        <div
                            className="rounded-xl overflow-hidden p-8 relative h-[300px] flex items-end"
                            style={{
                                background: `linear-gradient(to bottom right, 
                                rgba(${dominantColor?.[0]}, ${dominantColor?.[1]}, ${dominantColor?.[2]}, 0.8),
                                rgba(${dominantColor?.[0]}, ${dominantColor?.[1]}, ${dominantColor?.[2]}, 0.2)
                            )`
                            }}>
                            <div className="relative z-10 space-y-4">
                                <p className="text-sm text-white/90 font-medium tracking-wide uppercase">
                                    Personalized Playlist
                                </p>
                                <h2 className="text-5xl font-bold text-white">Your Mix #1</h2>
                                <p className="text-white/80 text-sm mb-2">
                                    Created just for you. Updated daily.
                                </p>
                                <button className="bg-white hover:bg-white/90 text-black px-8 py-3 rounded-full font-medium transition-all hover:scale-105">
                                    Play Now
                                </button>
                            </div>
                            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />
                        </div>

                        <section className="pr-6 pl-2 mt-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                                <div className="bg-[#0a0a0a] border border-white/5 rounded-lg">
                                    <div className="flex items-center justify-between p-4">
                                        <div className="flex items-center gap-2">
                                            <AudioWaveformIcon className="w-5 h-5 text-white/60" />
                                            <h4 className="text-white font-medium">
                                                {voiceState.voiceInfo?.current_channel?.name ||
                                                    "adam's channel"}
                                            </h4>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => setShowSettingsModal(true)}
                                                className="p-1 hover:bg-white/5 rounded transition-colors relative">
                                                <Settings className="w-4 h-4 text-white/40" />
                                            </button>
                                            <button className="p-1 hover:bg-white/5 rounded transition-colors">
                                                <Volume2 className="w-4 h-4 text-white/40" />
                                            </button>
                                        </div>
                                    </div>

                                    <div className="px-4 pb-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <img
                                                    src={
                                                        voiceState.voiceInfo?.current_channel
                                                            ?.listeners[0]?.avatar
                                                    }
                                                    alt=""
                                                    className="w-6 h-6 rounded-full"
                                                />
                                                <span className="text-sm text-white/60">
                                                    {voiceState.voiceInfo?.current_channel
                                                        ?.listeners.length || 1}{" "}
                                                    listener
                                                </span>
                                                <span className="text-white/40">•</span>
                                                <span className="text-sm text-white/60">
                                                    Not Connected
                                                </span>
                                            </div>

                                            <button className="px-4 py-1.5 bg-white/10 hover:bg-white/15 text-white text-sm rounded transition-colors">
                                                Join
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {(voiceState.voiceInfo?.available_channels ?? [])
                                    .filter(
                                        channel =>
                                            channel.id !== voiceState.voiceInfo?.current_channel?.id
                                    )
                                    .slice(0, 2)
                                    .map(channel => (
                                        <div
                                            key={channel.id}
                                            className="bg-[#0a0a0a] border border-white/5 rounded-lg p-4">
                                            <div className="flex items-center justify-between mb-3">
                                                <h5 className="text-white font-medium">
                                                    {channel.name}
                                                </h5>
                                                {channel.is_private && (
                                                    <span className="text-xs text-white/40">
                                                        private
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex items-center justify-between text-sm text-white/60">
                                                <span>{channel.member_count} listening</span>
                                                <span>
                                                    {channel.user_limit
                                                        ? `${channel.member_count}/${channel.user_limit}`
                                                        : "No limit"}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                            </div>
                        </section>

                        <div className="space-y-6 mr-2">
                            <section>
                                <div className="flex items-center justify-between mb-4 mt-4">
                                    <h3 className="text-xl font-bold text-white">
                                        Recently Played
                                    </h3>
                                    <button className="text-sm text-white/60 hover:text-white transition-colors">
                                        Show all
                                    </button>
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                                    {uniqueRecentlyPlayed?.map((track, i) => (
                                        <div
                                            key={i}
                                            className="bg-[#111111] rounded-lg p-3 hover:bg-[#222222] transition-colors group cursor-pointer">
                                            <div className="aspect-square rounded-lg relative mb-3 overflow-hidden">
                                                {track.artwork_url &&
                                                !failedImages.has(track.artwork_url) ? (
                                                    <img
                                                        src={track.artwork_url}
                                                        alt={track.title}
                                                        className="w-full h-full object-cover"
                                                        loading="lazy"
                                                        decoding="async"
                                                        onError={() =>
                                                            handleImageError(track.artwork_url)
                                                        }
                                                    />
                                                ) : (
                                                    <div className="w-full h-full animate-pulse bg-white/10" />
                                                )}
                                                <div className="absolute bottom-2 right-2 w-8 h-8 bg-evict-pink rounded-full items-center justify-center hidden group-hover:flex shadow-lg translate-y-2 group-hover:translate-y-0 transition-all">
                                                    <Play className="w-4 h-4 text-white" />
                                                </div>
                                            </div>
                                            <div className="text-white font-medium truncate text-sm mb-1">
                                                {track.title}
                                            </div>
                                            <div className="text-white/60 text-xs truncate">
                                                {track.author}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            <section>
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-xl font-bold text-white">Your Playlists</h3>
                                    <button
                                        onClick={() => setShowAllPlaylists(!showAllPlaylists)}
                                        className="text-sm text-white/60 hover:text-white transition-colors">
                                        {showAllPlaylists ? "Show less" : "Show all"}
                                    </button>
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                                    {musicData?.playlists
                                        .slice(0, showAllPlaylists ? undefined : 8) 
                                        .map((playlist, i) => (
                                            <div
                                                key={i}
                                                onClick={() => {
                                                    setSelectedPlaylist(playlist)
                                                    setCurrentView("playlist")
                                                }}
                                                className="bg-[#111111] rounded-lg p-3 hover:bg-[#222222] transition-colors group cursor-pointer">
                                                <div className="aspect-square rounded-lg relative mb-3 overflow-hidden grid grid-cols-2">
                                                    {playlist.tracks.slice(0, 4).map((track, j) => (
                                                        <img
                                                            key={j}
                                                            src={track.artwork_url}
                                                            alt=""
                                                            className="w-full h-full object-cover"
                                                        />
                                                    ))}
                                                    <div className="absolute bottom-2 right-2 w-8 h-8 bg-evict-pink rounded-full items-center justify-center hidden group-hover:flex shadow-lg translate-y-2 group-hover:translate-y-0 transition-all">
                                                        <Play className="w-4 h-4 text-white" />
                                                    </div>
                                                </div>
                                                <div className="text-white font-medium truncate text-sm mb-1">
                                                    {playlist.name}
                                                </div>
                                                <div className="text-white/60 text-xs truncate">
                                                    {playlist.track_count} songs
                                                </div>
                                            </div>
                                        ))}
                                </div>
                            </section>
                        </div>
                    </>
                )
        }
    }

    const renderStickyPlayer = () => {
        if (!playerState.current && isConnecting) {
            return (
                <>
                    <div className="lg:hidden">
                        <div className="p-4 animate-pulse">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-white/5 rounded"></div>
                                <div className="flex-1 space-y-2">
                                    <div className="h-3 bg-white/5 rounded w-32"></div>
                                    <div className="h-2 bg-white/5 rounded w-24"></div>
                                </div>
                                <div className="w-8 h-8 bg-white/5 rounded-full"></div>
                            </div>
                        </div>
                    </div>

                    <div className="hidden lg:block p-4">
                        <div className="mx-auto flex items-center justify-between px-6 animate-pulse">
                            <div className="flex items-center gap-4 flex-1">
                                <div className="w-14 h-14 bg-white/5 rounded"></div>
                                <div className="space-y-2">
                                    <div className="h-4 bg-white/5 rounded w-48"></div>
                                    <div className="h-3 bg-white/5 rounded w-32"></div>
                                </div>
                            </div>
                            <div className="flex-1 flex justify-center">
                                <div className="w-32 h-8 bg-white/5 rounded-full"></div>
                            </div>
                            <div className="flex-1"></div>
                        </div>
                    </div>
                </>
            )
        }

        if (!playerState.current) {
            return (
                <div className="flex items-center justify-between">
                    <div className="w-14 h-14 bg-white/5 rounded"></div>
                    <div className="flex-1 mx-4">
                        <div className="text-white/60">Not Playing</div>
                        <div className="text-sm text-white/40">Queue a song to get started</div>
                    </div>
                    <div className="text-xs text-white/60">0:00</div>
                </div>
            )
        }

        return (
            <div className="flex items-center justify-between">
                <img
                    src={playerState.current.thumbnail}
                    alt={playerState.current.title}
                    className="w-14 h-14 rounded object-cover"
                />
                <div className="flex-1 mx-4">
                    <div className="text-white font-medium truncate">
                        {playerState.current.title}
                    </div>
                    <div className="text-sm text-white/60 truncate">
                        {playerState.current.artist}
                    </div>
                </div>
                <div className="text-xs text-white/60">
                    {formatTime(playerState.current.position)}
                </div>
            </div>
        )
    }

    const renderNowPlaying = () => {
        if (!playerState.current) {
            return (
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="w-10 h-10 rounded overflow-hidden bg-white/10" />
                    <div className="min-w-0">
                        <div className="text-white/60 font-medium truncate text-sm">
                            Not Playing
                        </div>
                        <div className="text-white/40 text-xs truncate">
                            Queue a song to get started
                        </div>
                    </div>
                </div>
            )
        }

        console.log("🎵 Rendering now playing:", {
            title: playerState.current.title,
            artist: playerState.current.artist,
            thumbnail: playerState.current.thumbnail
        })

        return (
            <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className="w-10 h-10 rounded overflow-hidden bg-white/10">
                    {playerState.current.thumbnail && (
                        <img
                            src={playerState.current.thumbnail}
                            alt={playerState.current.title}
                            className="w-full h-full object-cover"
                        />
                    )}
                </div>
                <div className="min-w-0">
                    <div className="text-white font-medium truncate text-sm">
                        {playerState.current.title}
                    </div>
                    <div className="text-white/60 text-xs truncate">
                        {playerState.current.artist}
                    </div>
                </div>
            </div>
        )
    }

    const handleLyricSeek = (timestamp: number) => {
        sendMessage("SEEK", { position: timestamp })
    }

    useEffect(() => {
        console.log("Selected Playlist:", {
            name: selectedPlaylist?.name,
            trackCount: selectedPlaylist?.track_count,
            tracks: selectedPlaylist?.tracks?.length,
            firstTrack: selectedPlaylist?.tracks?.[0]
        })
    }, [selectedPlaylist])

    const QueueSection = () => {
        return (
            <div
                className={`
                fixed top-[70px] right-0 bottom-24 w-[400px] bg-[#111111] border-l border-white/10 
                transform transition-all duration-200
                ${showQueue ? "translate-x-0" : "translate-x-full"}
            `}>
                <div className="h-full flex flex-col">
                    <div className="flex items-center justify-between p-4 border-b border-white/10">
                        <h2 className="text-white text-lg font-medium">Queue</h2>
                        <button
                            onClick={() => setShowQueue(false)}
                            className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                            <X className="w-5 h-5 text-white/60" />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto">
                        {playerState.current && (
                            <div className="p-4 border-b border-white/10">
                                <div className="text-sm text-white/60 mb-3">Now Playing</div>
                                <div className="flex items-center gap-3">
                                    <img
                                        src={playerState.current.thumbnail}
                                        alt=""
                                        className="w-12 h-12 rounded"
                                    />
                                    <div className="flex-1 min-w-0">
                                        <div className="text-white font-medium truncate">
                                            {playerState.current.title}
                                        </div>
                                        <div className="text-sm text-white/60 truncate">
                                            {playerState.current.artist}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="p-4 border-b border-white/10">
                            <div className="text-sm text-white/60 mb-3">Queue</div>
                            <div className="space-y-2">
                                {playerState.queue?.map((track, i) => (
                                    <div
                                        key={i}
                                        className="flex items-center gap-3 p-2 hover:bg-white/5 rounded-lg group">
                                        <img
                                            src={track.thumbnail}
                                            alt=""
                                            className="w-12 h-12 rounded"
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="text-white font-medium truncate">
                                                {track.title}
                                            </div>
                                            <div className="text-sm text-white/60 truncate">
                                                {track.artist}
                                            </div>
                                        </div>
                                        <button className="p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <GripVertical className="w-4 h-4 text-white/40" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="p-4">
                            <div className="flex items-center justify-between mb-3">
                                <div className="text-sm text-white/60">Recommended</div>
                                <button
                                    onClick={() => fetchRecommendations()}
                                    className="p-1 hover:bg-white/5 rounded transition-colors">
                                    <RefreshCw
                                        className={`w-4 h-4 text-white/40 ${isLoadingRecommendations ? "animate-spin" : ""}`}
                                    />
                                </button>
                            </div>
                            <div className="space-y-2">
                                {recommendations.map((track, i) => (
                                    <div
                                        key={i}
                                        className="flex items-center gap-3 p-2 hover:bg-white/5 rounded-lg group">
                                        <img
                                            src={track.artworkUrl}
                                            alt=""
                                            className="w-12 h-12 rounded"
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="text-white font-medium truncate">
                                                {track.title}
                                            </div>
                                            <div className="text-sm text-white/60 truncate">
                                                {track.author}
                                            </div>
                                        </div>
                                        <button className="p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Plus className="w-4 h-4 text-white/40" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    useEffect(() => {
        const fetchTrackInfo = async () => {
            if (!playerState.current?.title) return

            const newTrackId = `${playerState.current.title}-${playerState.current.artist}`
            if (newTrackId === currentTrackId) return

            setCurrentTrackId(newTrackId)

            try {
                const response = await fetch(
                    `/api/song?title=${encodeURIComponent(playerState.current.title)}&artist=${encodeURIComponent(playerState.current.artist)}`
                )
                const data = await response.json()
                setTrackInfo(data)

                if (data.spotify?.trackId) {
                    const audioResponse = await fetch(
                        `https://listen.squareweb.app/video?spotifyId=${data.spotify.trackId}&key=evictiscool`
                    )
                    const audioData = await audioResponse.json()
                    setAudioUrl(audioData.url)
                }
            } catch (error) {
                console.error("Failed to fetch track info:", error)
            }
        }

        fetchTrackInfo()
    }, [playerState.current?.title, playerState.current?.artist])

    useEffect(() => {
        const fetchArtistInfo = async () => {
            if (!playerState.current?.artist) return

            try {
                const response = await fetch(
                    `/api/song?title=${encodeURIComponent(playerState.current.title)}&artist=${encodeURIComponent(playerState.current.artist)}`
                )
                const data = await response.json()
                setArtistInfo(data)
            } catch (error) {
                console.error("Failed to fetch artist info:", error)
            }
        }

        fetchArtistInfo()
    }, [playerState.current?.artist])

    return (
        <div className="space-y-6 flex select-none" onMouseDown={e => e.preventDefault()}>
            <div className={`flex-1 space-y-6 transition-all duration-200 pb-24`}>
                {currentView === "home" ? (
                    <div
                        className={`flex-1 space-y-6 transition-all duration-200 pb-24 pr-2 ${showLyrics ? "mr-[400px]" : ""}`}>
                        <div className="px-6 mb-6 flex items-center gap-3 -mt-3">
                            <div
                                className={`
                            flex items-center gap-2 bg-white/10 rounded-full h-12
                            ${isSearchExpanded ? "w-[300px]" : "w-12"} transition-all duration-300
                        `}
                                onMouseDown={e => e.stopPropagation()}>
                                <button
                                    onClick={() => {
                                        setIsSearchExpanded(!isSearchExpanded)
                                        if (!isSearchExpanded) {
                                            setTimeout(
                                                () => searchInputRef.current?.focus(),
                                                100
                                            )
                                        }
                                    }}
                                    className="p-3 h-full aspect-square">
                                    <Search className="w-5 h-5 text-white" />
                                </button>
                                <input
                                    ref={searchInputRef}
                                    type="text"
                                    value={searchQuery}
                                    placeholder="Search..."
                                    onChange={e => debouncedSearch(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === "Enter") {
                                            if (searchTimeoutRef.current) {
                                                clearTimeout(searchTimeoutRef.current)
                                            }
                                            performSearch(e.target.value)
                                        }
                                    }}
                                    className={`
                        bg-transparent text-white outline-none border-none
                        ${isSearchExpanded ? "w-full pr-4" : "w-0 opacity-0"}
                        transition-all duration-300
                    `}
                                />
                            </div>

                            <button
                                onClick={() =>
                                    setActiveTab(activeTab === "playlists" ? "all" : "playlists")
                                }
                                className={`
                                    px-6 py-3 rounded-full text-sm font-medium transition-all
                                    ${
                                        activeTab === "playlists"
                                            ? "bg-white text-black"
                                            : "bg-white/10 text-white hover:bg-white/20"
                                    }
                                `}>
                                Playlists
                            </button>

                            <button
                                onClick={() =>
                                    setActiveTab(activeTab === "recent" ? "all" : "recent")
                                }
                                className={`
                                    px-6 py-3 rounded-full text-sm font-medium transition-all
                                    ${
                                        activeTab === "recent"
                                            ? "bg-white text-black"
                                            : "bg-white/10 text-white hover:bg-white/20"
                                    }
                                `}>
                                Recently Played
                            </button>

                            {/* <button
                                onClick={() =>
                                    setActiveTab(activeTab === "discover" ? "all" : "discover")
                                }
                                className={`
                                    px-6 py-3 rounded-full text-sm font-medium transition-all
                                    ${
                                        activeTab === "discover"
                                            ? "bg-white text-black"
                                            : "bg-white/10 text-white hover:bg-white/20"
                                    }
                                `}>
                                Discover
                            </button> */}
                        </div>

                        {searchQuery ? (
                            <div className="px-6">
                                {isSearching ? (
                                    <div className="text-white/60 text-center py-8">
                                        Searching...
                                    </div>
                                ) : (
                                    <>
                                        {searchResults.tracks.length > 0 && (
                                            <section className="mb-8">
                                                <h2 className="text-xl font-bold text-white mb-4">
                                                    Songs
                                                </h2>
                                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                                                    {searchResults.tracks.map(
                                                        (track: any, i: number) => (
                                                            <div
                                                                key={i}
                                                                className="bg-[#111111] rounded-lg p-3 hover:bg-[#222222] transition-colors group cursor-pointer">
                                                                <div className="aspect-square rounded-lg relative mb-3 overflow-hidden bg-white/5">
                                                                    {track.artworkUrl &&
                                                                    !failedImages.has(
                                                                        track.artworkUrl
                                                                    ) ? (
                                                                        <img
                                                                            src={track.artworkUrl}
                                                                            alt={track.title}
                                                                            className="w-full h-full object-cover"
                                                                            loading="lazy"
                                                                            decoding="async"
                                                                            onError={() =>
                                                                                handleImageError(
                                                                                    track.artworkUrl
                                                                                )
                                                                            }
                                                                        />
                                                                    ) : (
                                                                        <div className="w-full h-full animate-pulse bg-white/10" />
                                                                    )}
                                                                    <div className="absolute bottom-2 right-2 w-8 h-8 bg-evict-pink rounded-full items-center justify-center hidden group-hover:flex shadow-lg translate-y-2 group-hover:translate-y-0 transition-all">
                                                                        <Play className="w-4 h-4 text-white" />
                                                                    </div>
                                                                </div>
                                                                <div className="text-white font-medium truncate text-sm mb-1">
                                                                    {track.title}
                                                                </div>
                                                                <div className="text-white/60 text-xs truncate">
                                                                    {track.author}
                                                                </div>
                                                            </div>
                                                        )
                                                    )}
                                                </div>
                                            </section>
                                        )}

                                        {searchResults.albums.length > 0 && (
                                            <section className="mb-8">
                                                <h2 className="text-xl font-bold text-white mb-4">
                                                    Albums
                                                </h2>
                                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                                                    {searchResults.albums.map(
                                                        (album: any, i: number) => (
                                                            <div
                                                                key={i}
                                                                className="bg-[#111111] rounded-lg p-3 hover:bg-[#222222] transition-colors group cursor-pointer">
                                                                <div className="aspect-square rounded-lg relative mb-3 overflow-hidden bg-white/5">
                                                                    {album.artworkUrl &&
                                                                    !failedImages.has(
                                                                        album.artworkUrl
                                                                    ) ? (
                                                                        <img
                                                                            src={album.artworkUrl}
                                                                            alt={album.name}
                                                                            className="w-full h-full object-cover"
                                                                            loading="lazy"
                                                                            decoding="async"
                                                                            onError={() =>
                                                                                handleImageError(
                                                                                    album.artworkUrl
                                                                                )
                                                                            }
                                                                        />
                                                                    ) : (
                                                                        <div className="w-full h-full animate-pulse bg-white/10" />
                                                                    )}
                                                                </div>
                                                                <div className="text-white font-medium truncate text-sm mb-1">
                                                                    {album.name}
                                                                </div>
                                                                <div className="text-white/60 text-xs truncate">
                                                                    {album.artist} • {album.tracks}{" "}
                                                                    tracks
                                                                </div>
                                                            </div>
                                                        )
                                                    )}
                                                </div>
                                            </section>
                                        )}

                                        {searchResults.playlists.length > 0 && (
                                            <section className="mb-8">
                                                <h2 className="text-xl font-bold text-white mb-4">
                                                    Playlists
                                                </h2>
                                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                                                    {searchResults.playlists.map(
                                                        (playlist: any, i: number) => (
                                                            <div
                                                                key={i}
                                                                className="bg-[#111111] rounded-lg p-3 hover:bg-[#222222] transition-colors group cursor-pointer">
                                                                <div className="aspect-square rounded-lg relative mb-3 overflow-hidden bg-white/5">
                                                                    {playlist.artworkUrl &&
                                                                    !failedImages.has(
                                                                        playlist.artworkUrl
                                                                    ) ? (
                                                                        <img
                                                                            src={
                                                                                playlist.artworkUrl
                                                                            }
                                                                            alt={playlist.name}
                                                                            className="w-full h-full object-cover"
                                                                            loading="lazy"
                                                                            decoding="async"
                                                                            onError={() =>
                                                                                handleImageError(
                                                                                    playlist.artworkUrl
                                                                                )
                                                                            }
                                                                        />
                                                                    ) : (
                                                                        <div className="w-full h-full animate-pulse bg-white/10" />
                                                                    )}
                                                                </div>
                                                                <div className="text-white font-medium truncate text-sm mb-1">
                                                                    {playlist.name}
                                                                </div>
                                                                <div className="text-white/60 text-xs truncate">
                                                                    By {playlist.author} •{" "}
                                                                    {playlist.tracks} tracks
                                                                </div>
                                                            </div>
                                                        )
                                                    )}
                                                </div>
                                            </section>
                                        )}

                                        {searchResults.artists.length > 0 && (
                                            <section className="mb-8">
                                                <h2 className="text-xl font-bold text-white mb-4">
                                                    Artists
                                                </h2>
                                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                                                    {searchResults.artists.map(
                                                        (artist: any, i: number) => (
                                                            <div
                                                                key={i}
                                                                className="bg-[#111111] rounded-lg p-3 hover:bg-[#222222] transition-colors group cursor-pointer">
                                                                <div className="aspect-square rounded-full relative mb-3 overflow-hidden bg-white/5">
                                                                    {artist.avatar &&
                                                                    !failedImages.has(
                                                                        artist.avatar
                                                                    ) ? (
                                                                        <img
                                                                            src={artist.avatar}
                                                                            alt={artist.name}
                                                                            className="w-full h-full object-cover"
                                                                            loading="lazy"
                                                                            decoding="async"
                                                                            onError={() =>
                                                                                handleImageError(
                                                                                    artist.avatar
                                                                                )
                                                                            }
                                                                        />
                                                                    ) : (
                                                                        <div className="w-full h-full animate-pulse bg-white/10 rounded-full" />
                                                                    )}
                                                                </div>
                                                                <div className="text-white font-medium truncate text-sm text-center">
                                                                    {artist.name}
                                                                </div>
                                                            </div>
                                                        )
                                                    )}
                                                </div>
                                            </section>
                                        )}

                                        {!isSearching &&
                                            searchResults.tracks.length === 0 &&
                                            searchResults.artists.length === 0 &&
                                            searchResults.albums.length === 0 &&
                                            searchResults.playlists.length === 0 && (
                                                <div className="text-white/60 text-center py-8">
                                                    No results found for &quot;{searchQuery}&quot;
                                                </div>
                                            )}
                                    </>
                                )}
                            </div>
                        ) : (
                            <>
                                {showArtistView ? (
                                    <div className="px-6 py-8 max-w-6xl mx-auto">
                                        <button
                                            onClick={() => setShowArtistView(false)}
                                            className="flex items-center gap-2 text-white/60 hover:text-white mb-8 transition-colors">
                                            <ChevronLeft className="w-5 h-5" />
                                            <span>Back</span>
                                        </button>

                                        <h1 className="text-5xl font-bold text-white mb-6">
                                            {artistInfo.artist.name}
                                        </h1>

                                        <div className="flex flex-wrap gap-3 mb-8">
                                            {artistInfo.artist.tags.map((tag: any) => (
                                                <span
                                                    key={tag.name}
                                                    className="px-3 py-1 bg-white/10 rounded-full text-white/60 text-sm">
                                                    {tag.name}
                                                </span>
                                            ))}
                                            <span className="text-white/40 text-sm">
                                                {artistInfo.artist.listeners.toLocaleString()}{" "}
                                                monthly listeners
                                            </span>
                                        </div>

                                        <div className="mb-12">
                                            <h2 className="text-2xl font-bold text-white mb-4">
                                                About
                                            </h2>
                                            <p className="text-white/80 leading-relaxed max-w-3xl">
                                                {artistInfo.artist.bio.split("<a")[0]}
                                            </p>
                                        </div>

                                        <div>
                                            <h2 className="text-2xl font-bold text-white mb-6">
                                                Fans Also Like
                                            </h2>
                                            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
                                                {artistInfo.artist.similar.map((artist: any) => (
                                                    <div key={artist.name} className="group">
                                                        <div className="aspect-square mb-3 rounded-full overflow-hidden bg-white/5">
                                                            {artist.image &&
                                                            !failedImages.has(
                                                                artist.image["#text"]
                                                            ) ? (
                                                                <img
                                                                    src={artist.image["#text"]}
                                                                    alt={artist.name}
                                                                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                                                    onError={() =>
                                                                        handleImageError(
                                                                            artist.image["#text"]
                                                                        )
                                                                    }
                                                                />
                                                            ) : (
                                                                <div className="w-full h-full animate-pulse bg-white/10 rounded-full" />
                                                            )}
                                                        </div>
                                                        <div className="text-sm font-medium text-white text-center">
                                                            {artist.name}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div>{renderContent()}</div>
                                )}
                            </>
                        )}
                    </div>
                ) : (
                    <div
                        className={`flex-1 space-y-4 transition-all duration-200 pb-24 ${showLyrics ? "mr-[400px]" : ""}`}>
                        <div
                            className="flex gap-6 items-end p-6"
                            style={{
                                background: `linear-gradient(180deg, 
                                    rgba(${playlistDominantColor?.[0] || 20}, ${playlistDominantColor?.[1] || 20}, ${playlistDominantColor?.[2] || 20}, 0.5) 0%,
                                    rgba(${playlistDominantColor?.[0] || 20}, ${playlistDominantColor?.[1] || 20}, ${playlistDominantColor?.[2] || 20}, 0.3) 30%,
                                    rgba(0, 0, 0, 0) 100%)`
                            }}>
                            <div className="w-40 h-40 rounded-lg overflow-hidden shadow-xl">
                                <div className="grid grid-cols-2 w-full h-full">
                                    {selectedPlaylist?.tracks
                                        .slice(0, 4)
                                        .map((track: any, i: number) => (
                                            <img
                                                key={i}
                                                src={track.artwork_url}
                                                alt=""
                                                className="w-full h-full object-cover"
                                            />
                                        ))}
                                </div>
                            </div>

                            <div className="flex-1">
                                <button
                                    onClick={() => setCurrentView("home")}
                                    className="text-white/60 hover:text-white mb-2 flex items-center gap-2">
                                    <ChevronLeft className="w-4 h-4" />
                                    Back to Home
                                </button>
                                <h1 className="text-4xl font-bold text-white mb-2">
                                    {selectedPlaylist?.name}
                                </h1>
                                <div className="text-white/60 text-sm">
                                    {selectedPlaylist?.track_count} songs
                                </div>
                            </div>
                        </div>

                        <div className="px-6 space-y-4">
                            <div className="flex items-center gap-3">
                                <button className="bg-evict-pink hover:bg-evict-pink/90 text-white px-6 py-2.5 rounded-full font-medium transition-all hover:scale-105 flex items-center gap-2 text-sm">
                                    <Play className="w-4 h-4" fill="currentColor" />
                                    Play
                                </button>
                                <button className="bg-white/10 hover:bg-white/15 text-white px-6 py-2.5 rounded-full font-medium transition-all hover:scale-105 flex items-center gap-2 text-sm">
                                    <svg
                                        width="16"
                                        height="16"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2">
                                        <path d="M16 3 L21 8 L16 13" />
                                        <path d="M4 20 L21 20 L21 8" />
                                        <path d="M4 8 L9 3 L14 8" />
                                        <path d="M4 16 L4 4" />
                                    </svg>
                                    Shuffle
                                </button>
                            </div>

                            <div className="flex items-center gap-4">
                                <div className="relative flex-1 max-w-md">
                                    <input
                                        ref={searchInputRef}
                                        type="text"
                                        value={playlistFilter}
                                        onChange={e => setPlaylistFilter(e.target.value)}
                                        onFocus={() => setIsSearchFocused(true)}
                                        onBlur={() => setIsSearchFocused(false)}
                                        onClick={() => searchInputRef.current?.focus()}
                                        placeholder="Filter playlist"
                                        className={`
                                            w-full bg-white/5 border rounded-full px-4 py-2 text-sm text-white 
                                            placeholder:text-white/40 focus:outline-none transition-colors
                                            ${isSearchFocused ? "border-white/20" : "border-white/10"}
                                        `}
                                    />
                                    <button
                                        onClick={() => searchInputRef.current?.focus()}
                                        className="absolute right-4 top-1/2 -translate-y-1/2">
                                        <Search
                                            className={`
                                            w-4 h-4 transition-colors
                                            ${isSearchFocused ? "text-white/60" : "text-white/40"}
                                        `}
                                        />
                                    </button>
                                </div>
                                <select
                                    value={playlistSort}
                                    onChange={e =>
                                        setPlaylistSort(e.target.value as typeof playlistSort)
                                    }
                                    className="w-full md:w-auto bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white 
                                        appearance-none cursor-pointer hover:bg-white/10 transition-colors focus:border-white/20 focus:outline-none">
                                    <option value="custom">Custom order</option>
                                    <option value="title">Title</option>
                                    <option value="artist">Artist</option>
                                    <option value="album">Album</option>
                                    <option value="date_added">Date added</option>
                                    <option value="duration">Duration</option>
                                </select>
                            </div>
                        </div>

                        <div className="px-6">
                            <div className="border-b border-white/10 pb-2 mb-2">
                                <div className="grid grid-cols-[16px_4fr_3fr_minmax(120px,1fr)] gap-4 text-xs text-white/40 px-4">
                                    <div>#</div>
                                    <div>Title</div>
                                    <div>Album</div>
                                    <div className="flex justify-end">
                                        <Clock className="w-3.5 h-3.5" />
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-1">
                                {selectedPlaylist?.tracks ? (
                                    filteredAndSortedTracks.map((track: any, i: number) => (
                                        <div
                                            key={i}
                                            className="grid grid-cols-[16px_4fr_3fr_minmax(120px,1fr)] gap-4 p-2 rounded-lg hover:bg-white/5 group transition-colors cursor-pointer">
                                            <div className="text-white/40 text-sm self-center">
                                                {i + 1}
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <img
                                                    src={track.artwork_url}
                                                    alt=""
                                                    className="w-10 h-10 rounded"
                                                />
                                                <div>
                                                    <div className="text-white text-sm font-medium">
                                                        {track.title}
                                                    </div>
                                                    <div className="text-sm text-white/60">
                                                        {track.author}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="hidden md:block text-white/60 text-sm self-center">
                                                {track.album}
                                            </div>
                                            <div className="hidden md:block text-white/60 text-sm text-right self-center">
                                                {formatTime(track.duration)}
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center py-8 text-white/40">
                                        Loading playlist...
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <div
                className={`
                fixed bottom-24 right-8 w-[300px] bg-black/95 p-4 rounded-xl
                transition-all duration-200 z-50 border border-white/10 backdrop-blur-lg
                ${showFilters ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0 pointer-events-none"}
            `}>
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-white font-medium">Audio Effects</h3>
                    <button
                        onClick={() => setShowFilters(false)}
                        className="hover:bg-white/5 p-1 rounded-lg transition-colors">
                        <X className="w-5 h-5 text-white/60" />
                    </button>
                </div>

                <div className="space-y-6">
                    {[
                        {
                            name: "Bass Boost",
                            icon: <Waves className="w-4 h-4" />,
                            value: filters.bassboost,
                            key: "bassboost"
                        },
                        {
                            name: "Nightcore",
                            icon: <AudioWaveformIcon className="w-4 h-4" />,
                            value: filters.nightcore,
                            key: "nightcore"
                        },
                        {
                            name: "Reverb",
                            icon: <Volume2 className="w-4 h-4" />,
                            value: filters.reverb,
                            key: "reverb"
                        }
                    ].map(filter => (
                        <div key={filter.key} className="space-y-2">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 text-white/60">
                                    {filter.icon}
                                    <span className="text-white/90 text-sm">{filter.name}</span>
                                </div>
                                <span className="text-xs text-white/60">{filter.value}%</span>
                            </div>
                            <div className="relative h-1 bg-white/10 rounded-full">
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={filter.value}
                                    onChange={e =>
                                        setFilters(prev => ({
                                            ...prev,
                                            [filter.key]: parseInt(e.target.value)
                                        }))
                                    }
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                />
                                <div
                                    className="h-full bg-evict-pink rounded-full transition-all"
                                    style={{ width: `${filter.value}%` }}
                                />
                                <div
                                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg transition-all"
                                    style={{
                                        left: `${filter.value}%`,
                                        transform: `translate(-50%, -50%)`
                                    }}
                                />
                            </div>
                        </div>
                    ))}
                </div>

                <button
                    onClick={() => setFilters({ bassboost: 0, nightcore: 0, reverb: 0 })}
                    className="w-full mt-6 py-2 text-sm text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                    Reset All
                </button>
            </div>

            <ExpandedMobilePlayer />

            <div
                className={`
                fixed bottom-0 inset-x-0 bg-[#111111] border-t border-[#222222]
                transition-all duration-200 z-[9999]
            `}>
                <div className="lg:pl-64 transition-all duration-200">
                    <div className="lg:hidden">
                        <div className="p-4 flex items-center justify-between">
                            {renderNowPlaying()}
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
                                    onClick={() => setIsPlayerExpanded(!isPlayerExpanded)}
                                    className="p-2">
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
                                    <Volume2 className="w-5 h-5 text-white/60" />
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
                                    onClick={() => setShowLyrics(!showLyrics)}
                                    className={`p-2 hover:bg-white/5 rounded-lg transition-colors ${showLyrics ? "text-evict-pink" : "text-white/60"}`}>
                                    <Mic2 className="w-5 h-5" />
                                </button>
                                <button
                                    onClick={() => setShowQueue(!showQueue)}
                                    className={`p-2 hover:bg-white/5 rounded-lg transition-colors ${showQueue ? "text-evict-pink" : "text-white/60"}`}>
                                    <ListMusic className="w-5 h-5" />
                                </button>
                                <button
                                    onClick={() => setShowFilters(!showFilters)}
                                    className={`p-2 hover:bg-white/5 rounded-lg transition-colors ${showFilters ? "text-evict-pink" : "text-white/60"}`}>
                                    <AudioWaveformIcon className="w-5 h-5" />
                                </button>
                                <div className="w-24 h-1 bg-white/10 rounded-full">
                                    <div className="w-1/2 h-full bg-white rounded-full" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="h-24" />
            <SettingsModal />
            <QueueSection />

            {isSearchExpanded &&
                (searchResults.tracks.length > 0 || searchResults.artists.length > 0) && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-[#111111] rounded-lg border border-white/10 shadow-xl z-50 max-h-[70vh] overflow-y-auto">
                        {searchResults.artists.length > 0 && (
                            <div className="p-4">
                                <h3 className="text-white/60 text-sm mb-3">Artists</h3>
                                <div className="grid grid-cols-2 gap-4">
                                    {searchResults.artists.map((artist, i) => (
                                        <div
                                            key={i}
                                            className="flex items-center gap-3 p-2 hover:bg-white/5 rounded-lg cursor-pointer">
                                            <img
                                                src={artist.image}
                                                alt={artist.name}
                                                className="w-12 h-12 rounded-full object-cover"
                                            />
                                            <div>
                                                <div className="text-white font-medium">
                                                    {artist.name}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {searchResults.tracks.length > 0 && (
                            <div className="p-4 border-t border-white/10">
                                <h3 className="text-white/60 text-sm mb-3">Songs</h3>
                                <div className="space-y-2">
                                    {searchResults.tracks.map((track, i) => (
                                        <div
                                            key={i}
                                            className="flex items-center gap-3 p-2 hover:bg-white/5 rounded-lg cursor-pointer">
                                            <img
                                                src={track.image}
                                                alt={track.name}
                                                className="w-12 h-12 rounded object-cover"
                                            />
                                            <div>
                                                <div className="text-white font-medium">
                                                    {track.name}
                                                </div>
                                                <div className="text-white/60 text-sm">
                                                    {track.artist}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {isSearching && (
                            <div className="p-4 text-center text-white/60">Searching...</div>
                        )}
                    </div>
                )}
        </div>
    )
}
