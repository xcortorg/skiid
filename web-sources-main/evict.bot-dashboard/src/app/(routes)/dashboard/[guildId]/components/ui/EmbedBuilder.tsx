"use client"

import DiscordEmbed from "@/components/ticket/components/DiscordEmbed"
import DiscordMessage from "@/components/ticket/components/DiscordMessage"
import DiscordMessages from "@/components/ticket/components/DiscordMessages"
import { Dialog } from "@headlessui/react"
import { Check, Save, X } from "lucide-react"
import { useEffect, useState } from "react"
import { create } from "zustand"

interface EmbedState {
    color: string
    title?: string
    description?: string
    timestamp?: boolean
    author?: {
        name?: string
        icon_url?: string
    }
    image?: string
    thumbnail?: string
    footer?: {
        text?: string
        icon_url?: string
    }
    content?: string
}

export interface EmbedBuilderProps {
    value: string
    onChange: (value: string) => void
}

const validateScript = (script: string): string | null => {
    if (!script.startsWith("{embed}")) {
        return "Script must start with {embed}"
    }
    if (!script.includes("{color:")) {
        return "Script must include a color using {color: #hexcode}"
    }

    const openCount = (script.match(/{/g) || []).length
    const closeCount = (script.match(/}/g) || []).length
    if (openCount !== closeCount) {
        return "Mismatched brackets in script"
    }

    const sections = [
        "title:",
        "description:",
        "author:",
        "image:",
        "thumbnail:",
        "footer:",
        "timestamp"
    ]
    const scriptLower = script.toLowerCase()
    for (const section of sections) {
        const idx = scriptLower.indexOf(section)
        if (idx !== -1 && !scriptLower.includes("$v{" + section)) {
            return `Section '${section}' must be prefixed with $v{`
        }
    }

    return null
}

interface EmbedBuilderStore {
    isOpen: boolean
    value: string
    onSave: ((value: string) => void) | null
    open: (value: string, onSave: (value: string) => void) => void
    close: () => void
}

const useEmbedBuilderStore = create<EmbedBuilderStore>((set) => ({
    isOpen: false,
    value: "",
    onSave: null,
    open: (value: string, onSave: (value: string) => void) => set(state => ({
        isOpen: true,
        value,
        onSave,
        embed: { color: "#000000" }
    })),
    close: () => set({ isOpen: false, value: "", onSave: null })
}))

export function useEmbedBuilder() {
    const { open } = useEmbedBuilderStore()
    return { openBuilder: open }
}

export function EmbedBuilder() {
    const { isOpen, value: currentValue, onSave: handleSave, close } = useEmbedBuilderStore()
    const [embed, setEmbed] = useState<EmbedState>({
        color: "#000000"
    })

    useEffect(() => {
        if (currentValue) {
            const parsedEmbed = parseScript(currentValue)
            setEmbed({ color: "#000000", ...parsedEmbed })
        }
    }, [currentValue])

    const updateEmbed = (updates: Partial<EmbedState>) => {
        setEmbed(prev => ({ ...prev, ...updates }))
    }

    return (
        <>

            <Dialog
                open={isOpen}
                onClose={() => close()}
                className="relative z-50"
            >
                <div className="fixed inset-0 bg-black/50" aria-hidden="true" />

                <div className="fixed inset-0 flex items-center justify-center p-4">
                    <Dialog.Panel className="relative bg-[#0B0C0C] p-6 rounded-xl border border-[#222222] w-[95vw] max-w-[800px] max-h-[90vh] overflow-y-auto">
                        <button 
                            onClick={() => close()}
                            className="absolute top-4 right-4 hover:bg-white/5 p-1 rounded transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                        <Dialog.Title className="text-lg font-semibold mb-4">
                            Embed Builder
                        </Dialog.Title>

                        <div className="mb-6 bg-[#313338] rounded-xl p-4">
                            <DiscordMessages>
                                <DiscordMessage
                                    author="evict"
                                    avatar="https://r2.evict.bot/evict-new.png"
                                    bot={true}>
                                    <DiscordEmbed
                                        embedTitle={embed.title}
                                        authorName={embed.author?.name}
                                        authorIcon={embed.author?.icon_url}
                                        image={embed.image}
                                        thumbnail={embed.thumbnail}
                                        borderColor={embed.color}
                                        timestamp={embed.timestamp ? new Date() : undefined}
                                        footerIcon={embed.footer?.icon_url}>
                                        {embed.description}
                                        {embed.footer?.text && (
                                            <div slot="footer">{embed.footer.text}</div>
                                        )}
                                    </DiscordEmbed>
                                </DiscordMessage>
                            </DiscordMessages>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm mb-2">Color</label>
                                    <div className="flex gap-2 items-center">
                                        <input
                                            type="color"
                                            value={embed.color}
                                            onChange={e => updateEmbed({ color: e.target.value })}
                                            className="w-10 h-10 rounded-lg cursor-pointer border border-[#222222] bg-[#0B0C0C] p-1"
                                        />
                                        <input
                                            type="text"
                                            value={embed.color}
                                            onChange={e => updateEmbed({ color: e.target.value })}
                                            className="flex-1 bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2"
                                            placeholder="#000000"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm mb-2">Title</label>
                                    <input
                                        type="text"
                                        value={embed.title || ""}
                                        onChange={e => updateEmbed({ title: e.target.value })}
                                        className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm mb-2">Description</label>
                                    <textarea
                                        value={embed.description || ""}
                                        onChange={e => updateEmbed({ description: e.target.value })}
                                        className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2 min-h-[100px]"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm mb-2">Author</label>
                                    <div className="space-y-2">
                                        <input
                                            type="text"
                                            placeholder="Author Name"
                                            value={embed.author?.name || ""}
                                            onChange={e =>
                                                updateEmbed({
                                                    author: { ...embed.author, name: e.target.value }
                                                })
                                            }
                                            className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2"
                                        />
                                        <input
                                            type="text"
                                            placeholder="Author Icon URL"
                                            value={embed.author?.icon_url || ""}
                                            onChange={e =>
                                                updateEmbed({
                                                    author: {
                                                        ...embed.author,
                                                        icon_url: e.target.value
                                                    }
                                                })
                                            }
                                            className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm mb-2">Image URL</label>
                                    <input
                                        type="text"
                                        value={embed.image || ""}
                                        onChange={e => updateEmbed({ image: e.target.value })}
                                        className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2"
                                        placeholder="https://example.com/image.png"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm mb-2">Thumbnail URL</label>
                                    <input
                                        type="text"
                                        value={embed.thumbnail || ""}
                                        onChange={e => updateEmbed({ thumbnail: e.target.value })}
                                        className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2"
                                        placeholder="https://example.com/thumbnail.png"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm mb-2">Footer</label>
                                    <div className="space-y-2">
                                        <input
                                            type="text"
                                            placeholder="Footer Text"
                                            value={embed.footer?.text || ""}
                                            onChange={e =>
                                                updateEmbed({
                                                    footer: { ...embed.footer, text: e.target.value }
                                                })
                                            }
                                            className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2"
                                        />
                                        <input
                                            type="text"
                                            placeholder="Footer Icon URL"
                                            value={embed.footer?.icon_url || ""}
                                            onChange={e =>
                                                updateEmbed({
                                                    footer: {
                                                        ...embed.footer,
                                                        icon_url: e.target.value
                                                    }
                                                })
                                            }
                                            className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2"
                                        />
                                    </div>
                                </div>

                                <div className="flex items-center gap-3">
                                    <div
                                        className={`w-5 h-5 rounded-md border ${
                                            embed.timestamp
                                                ? "bg-blue-600 border-blue-600"
                                                : "border-[#222222] bg-[#0B0C0C]"
                                        } flex items-center justify-center transition-colors cursor-pointer`}
                                        onClick={() => updateEmbed({ timestamp: !embed.timestamp })}>
                                        {embed.timestamp && (
                                            <Check className="w-3.5 h-3.5 text-white" />
                                        )}
                                    </div>
                                    <label className="text-sm cursor-pointer">Include Timestamp</label>
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 flex justify-end">
                            <button
                                onClick={() => {
                                    handleSave?.(generateScript(embed))
                                    close()
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-[#0B0C0C] text-white rounded-xl border border-[#222222] hover:bg-[#151515] transition-colors"
                            >
                                <Save className="w-4 h-4" />
                                <span>Save Embed</span>
                            </button>
                        </div>
                    </Dialog.Panel>
                </div>
            </Dialog>
        </>
    )
}

function generateScript(embed: EmbedState): string {
    let script = `{embed}{color: ${embed.color}}`

    if (embed.title) script += `$v{title: ${embed.title}}`
    if (embed.description) script += `$v{description: ${embed.description}}`
    if (embed.timestamp) script += `$v{timestamp}`
    if (embed.author?.name || embed.author?.icon_url) {
        script += `$v{author: `
        if (embed.author.name) script += `name: ${embed.author.name}`
        if (embed.author.icon_url) {
            if (embed.author.name) script += " && "
            script += `icon: ${embed.author.icon_url}`
        }
        script += `}`
    }
    if (embed.thumbnail) script += `$v{thumbnail: ${embed.thumbnail}}`
    if (embed.image) script += `$v{image: ${embed.image}}`
    if (embed.footer?.text || embed.footer?.icon_url) {
        script += `$v{footer: `
        if (embed.footer.text) script += `text: ${embed.footer.text}`
        if (embed.footer.icon_url) {
            if (embed.footer.text) script += " && "
            script += `icon: ${embed.footer.icon_url}`
        }
        script += `}`
    }

    return script
}

export function parseScript(script: string): Partial<EmbedState> {
    const embed: Partial<EmbedState> = {}

    const colorMatch = script.match(/{color:\s*([^}]+)}/)
    if (colorMatch) embed.color = colorMatch[1].trim()

    const titleMatch = script.match(/\$v{title:\s*([^}]+)}/)
    if (titleMatch) embed.title = titleMatch[1].trim()

    const descMatch = script.match(/\$v{description:\s*([^}]+)}/)
    if (descMatch) embed.description = descMatch[1].trim()

    const thumbnailMatch = script.match(/\$v{thumbnail:\s*([^}]+)}/)
    if (thumbnailMatch) embed.thumbnail = thumbnailMatch[1].trim()

    const imageMatch = script.match(/\$v{image:\s*([^}]+)}/)
    if (imageMatch) embed.image = imageMatch[1].trim()

    embed.timestamp = script.includes("$v{timestamp}")

    const authorMatch = script.match(/\$v{author:\s*([^}]+)}/)
    if (authorMatch) {
        const authorContent = authorMatch[1]
        embed.author = {}
        const nameMatch = authorContent.match(/name:\s*([^&&}]+)/)
        const iconMatch = authorContent.match(/icon:\s*([^&&}]+)/)
        if (nameMatch) embed.author.name = nameMatch[1].trim()
        if (iconMatch) embed.author.icon_url = iconMatch[1].trim()
    }

    const footerMatch = script.match(/\$v{footer:\s*([^}]+)}/)
    if (footerMatch) {
        const footerContent = footerMatch[1]
        const textMatch = footerContent.match(/text:\s*([^&&}]+)/)
        const iconMatch = footerContent.match(/icon:\s*([^&&}]+)/)
        embed.footer = {}
        if (textMatch) embed.footer.text = textMatch[1].trim()
        if (iconMatch) embed.footer.icon_url = iconMatch[1].trim()
    }

    return embed
}
