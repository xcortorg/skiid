"use client"

import { format } from "date-fns"
import Image from "next/image"
import { useEffect, useState } from "react"

interface Avatar {
    url: string
    timestamp: string
}

interface User {
    id: string
    name: string
    discriminator: string
    avatar: string
    display_name: string
}

interface AvatarHistory {
    user: User
    avatars: Avatar[]
    total: number
}

const AvatarPage = ({ params }: { params: { slug: string } }) => {
    const [data, setData] = useState<AvatarHistory | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const fetchAvatars = async () => {
            try {
                const response = await fetch(`/api/avatars/${params.slug}`)
                if (!response.ok) {
                    const errorData = await response.json()
                    throw new Error(errorData.error || "Failed to fetch avatars")
                }
                const data = await response.json()
                setData(data)
            } catch (err) {
                setError(err instanceof Error ? err.message : "Failed to load avatar history")
            } finally {
                setLoading(false)
            }
        }

        fetchAvatars()
    }, [params.slug])

    if (loading) {
        return (
            <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
                <div className="text-white/60">Loading...</div>
            </div>
        )
    }

    if (error || !data) {
        return (
            <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
                <div className="w-full">
                    <div className="relative border-b border-white/5 bg-black/20">
                        <div className="absolute inset-0 top-0 bg-[url('/noise.png')] opacity-5" />
                        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-12 relative">
                            <div className="flex flex-col items-center justify-center text-center">
                                <h1 className="font-bold text-4xl sm:text-5xl text-white mb-4">
                                    No Avatars Found
                                </h1>
                                <p className="text-white/60 mb-8 max-w-3xl mx-auto">
                                    This user has no saved avatar history yet.
                                </p>

                                <div className="w-full max-w-md mb-8">
                                    <form
                                        onSubmit={e => {
                                            e.preventDefault()
                                            const form = e.target as HTMLFormElement
                                            const input = form.elements.namedItem(
                                                "userId"
                                            ) as HTMLInputElement
                                            if (input.value) {
                                                window.location.href = `/avatars/${input.value}`
                                            }
                                        }}
                                        className="relative">
                                        <input
                                            type="text"
                                            name="userId"
                                            placeholder="Enter a Discord User ID..."
                                            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white 
                                     placeholder:text-white/40 focus:outline-none focus:border-white/20 transition-colors"
                                        />
                                        <button
                                            type="submit"
                                            className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1 bg-white/10 
                                     hover:bg-white/20 rounded text-sm text-white transition-colors">
                                            Search
                                        </button>
                                    </form>
                                </div>

                                <div className="flex flex-col sm:flex-row gap-4 items-center">
                                    <a
                                        href="/"
                                        className="px-6 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-white 
                                       transition-colors flex items-center gap-2">
                                        Return Home
                                    </a>
                                    <a
                                        href="/commands"
                                        className="px-6 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-white 
                                       transition-colors flex items-center gap-2">
                                        View Commands
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-[#0A0A0B]">
            <div className="relative border-b border-white/5 bg-black/20">
                <div className="absolute inset-0 top-0 bg-[url('/noise.png')] opacity-5" />
                <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-12 pt-24 relative">
                    <div className="flex items-center gap-6">
                        <div className="relative w-20 h-20 rounded-full overflow-hidden border-2 border-white/10">
                            <Image
                                src={data.user.avatar}
                                alt={data.user.name}
                                fill
                                unoptimized
                                className="object-cover"
                            />
                        </div>
                        <div>
                            <h1 className="font-bold text-4xl sm:text-5xl text-white">
                                {data.user.display_name}
                            </h1>
                            <p className="text-white/60 mt-2">
                                {data.total} avatar{data.total !== 1 ? "s" : ""} saved
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-8">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {data.avatars.map((avatar, index) => (
                        <div
                            key={avatar.timestamp}
                            className="group relative bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden transition-all hover:border-white/10">
                            <div className="aspect-square relative">
                                <Image
                                    src={avatar.url}
                                    alt={`Avatar ${index + 1}`}
                                    fill
                                    unoptimized
                                    className="object-cover"
                                />
                            </div>
                            <div className="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black/90 to-transparent">
                                <p className="text-white/60 text-sm">
                                    {format(new Date(avatar.timestamp), "MMMM d, yyyy 'at' h:mm a")}{" "}
                                    UTC
                                </p>
                            </div>
                            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 flex items-center justify-center">
                                <a
                                    href={avatar.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white text-sm transition-colors">
                                    View Original
                                </a>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

export default AvatarPage
