"use client"

import { createContext, useContext, useState } from 'react'

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

interface LyricsResult {
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

interface MusicContextType {
    playerState: PlayerState
    setPlayerState: (state: PlayerState) => void
    showLyrics: boolean
    setShowLyrics: (show: boolean) => void
    lyrics: LyricsResult | null
    setLyrics: (lyrics: LyricsResult | null) => void
    currentTime: number
    setCurrentTime: (time: number) => void
    controls: {
        play: () => void
        pause: () => void
        skip: () => void
        seek: (position: number) => void
        setVolume: (volume: number) => void
        toggleShuffle: () => void
        setRepeat: (mode: "track" | "queue" | "off") => void
        togglePlay: () => void
    }
    sendMessage: (type: string, data: any) => void
    showArtistView: boolean
    setShowArtistView: (show: boolean) => void
    artistInfo: any
    setArtistInfo: (info: any) => void
}

export const MusicContext = createContext<MusicContextType | null>(null)

export const useMusicContext = () => {
    const context = useContext(MusicContext)
    if (!context) {
        throw new Error('useMusicContext must be used within a MusicProvider')
    }
    return context
}

export type { PlayerState, LyricsResult, Track } 