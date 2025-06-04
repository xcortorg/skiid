"use client"

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { MusicContext, PlayerState, LyricsResult } from './music-context'

export function MusicProvider({ children }: { children: React.ReactNode }) {
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
    const [showLyrics, setShowLyrics] = useState(false)
    const [lyrics, setLyrics] = useState<LyricsResult | null>(null)
    const [currentTime, setCurrentTime] = useState(0)
    const [showArtistView, setShowArtistView] = useState(false)
    const [artistInfo, setArtistInfo] = useState<any>(null) 

    const processedTracks = useRef<Set<string>>(new Set())

    const controls = {
        togglePlay: () => {},
        play: () => {},
        pause: () => {},
        skip: () => {},
        seek: (position: number) => {},
        setVolume: (volume: number) => {},
        toggleShuffle: () => {},
        setRepeat: (mode: "track" | "queue" | "off") => {}
    }

    const handleStateUpdate = useCallback((state: any) => {
        console.log("🎵 MusicProvider handling state update:", state)
        
        setPlayerState(prevState => {
            const newState = {
                ...prevState,
                ...state,
                current: state.current ? {
                    ...(prevState.current || {}),
                    ...state.current,
                    position: state.current.position || 0,
                    is_playing: state.current.is_playing
                } : null,
                queue: state.queue || [],
                controls: {
                    ...prevState.controls,
                    ...state.controls
                }
            }
            
            console.log("🎵 Updated player state:", newState)
            return newState
        })

        if (state.current?.position !== undefined) {
            setCurrentTime(state.current.position)
        }
    }, [])

    const value = useMemo(() => ({
        playerState,
        setPlayerState,
        showLyrics,
        setShowLyrics,
        lyrics,
        setLyrics,
        currentTime,
        setCurrentTime,
        controls,
        showArtistView,
        setShowArtistView,
        artistInfo,
        setArtistInfo,
        handleStateUpdate,
        sendMessage: (type: string, data?: any) => {
            console.log("Provider sendMessage called:", type, data)
        }
    }), [
        playerState,
        showLyrics,
        lyrics,
        currentTime,
        controls,
        showArtistView,
        artistInfo,
        handleStateUpdate
    ])

    useEffect(() => {
        const updateQueueArtwork = async () => {
            if (!playerState.queue?.length) return

            const updatedQueue = await Promise.all(
                playerState.queue.map(async (track) => {
                    const trackId = `${track.title}-${track.artist}`
                    
                    if (processedTracks.current.has(trackId)) return track
                    
                    try {
                        const response = await fetch(`/api/deezer/search?q=${encodeURIComponent(`${track.title} ${track.artist}`)}`)
                        const data = await response.json()
                        const artwork = data.data?.[0]?.album?.cover_big

                        if (artwork) {
                            processedTracks.current.add(trackId)
                            return { ...track, thumbnail: artwork }
                        }
                    } catch (error) {
                        console.error('Failed to fetch Deezer artwork:', error)
                    }
                    
                    return track
                })
            )

            setPlayerState(prev => ({
                ...prev,
                queue: updatedQueue
            }))
        }

        updateQueueArtwork()
    }, [playerState.queue?.length])

    return (
        <MusicContext.Provider value={value}>
            {children}
        </MusicContext.Provider>
    )
} 