"use client"

import { useState, useEffect } from "react"
import Image from "next/image"

export default function UserAvatar() {
    const [userImage, setUserImage] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const image = localStorage.getItem('userImage')
        setUserImage(image)
        setLoading(false)
    }, [])

    if (loading) {
        return <div className="w-8 h-8 rounded-full bg-gray-600 animate-pulse" />
    }

    if (!userImage) return null

    return (
        <Image
            src={userImage}
            alt="Avatar"
            width={32}
            height={32}
            className="rounded-full"
        />
    )
} 