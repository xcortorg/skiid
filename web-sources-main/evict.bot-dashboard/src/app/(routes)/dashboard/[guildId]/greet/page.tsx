"use client"

import { fetchGuildChannels } from "@/libs/dashboard/guild"
import { fetchGuildGreetings, type GreetingsResponse, type GreetingsUpdate } from "@/libs/dashboard/guild/greetings"
import { useQuery } from "@tanstack/react-query"
import { Code, Hash, MessageSquare, Plus, UserMinus, UserPlus, Trash2 } from "lucide-react"
import { useState, useEffect, memo } from "react"
import SaveButton from "../components/security/SaveButton"
import Dropdown from "../components/ui/Dropdown"
import { EmbedBuilder, useEmbedBuilder } from "../components/ui/EmbedBuilder"
import { toast } from "react-hot-toast"
import { updateGuildGreetings } from "@/libs/dashboard/guild/greetings"

function Switch({ checked, onCheckedChange }: { checked: boolean; onCheckedChange: (checked: boolean) => void }) {
    return (
        <button
            onClick={() => onCheckedChange(!checked)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                checked ? "bg-blue-600" : "bg-white/10"
            }`}>
            <span className={`${checked ? "translate-x-6" : "translate-x-1"} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
        </button>
    )
}

const MessageSection = memo(({ 
    type, 
    messages, 
    onAdd, 
    maxMessages,
    onUpdate,
    onDelete,
    channels 
}: { 
    type: "welcome" | "goodbye"
    messages: Array<{
        channel: { id: string; name: string; type: string }
        content: string
        delete_after: number
    }>
    onAdd: () => void
    maxMessages: number
    onUpdate: (index: number, updates: Partial<typeof messages[0]>) => void
    onDelete: (index: number) => void
    channels: any[]
}) => {
    const { openBuilder } = useEmbedBuilder()

    return (
        <div className="bg-[#141414] border border-white/5 rounded-xl">
            <div className="p-4 border-b border-white/5">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {type === "welcome" ? (
                            <UserPlus className="w-5 h-5 text-white/60" />
                        ) : (
                            <UserMinus className="w-5 h-5 text-white/60" />
                        )}
                        <h2 className="text-base font-medium text-white">
                            {type === "welcome" ? "Welcome" : "Goodbye"} Messages ({messages.length}/{maxMessages})
                        </h2>
                    </div>
                    <button
                        onClick={onAdd}
                        disabled={messages.length >= maxMessages}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg 
                                 hover:bg-blue-700 transition-colors text-sm disabled:opacity-50 
                                 disabled:cursor-not-allowed">
                        <Plus className="w-4 h-4" />
                        Add Message
                    </button>
                </div>
            </div>

            <div className="p-4 space-y-4">
                {messages.length === 0 ? (
                    <div className="text-center py-12">
                        <MessageSquare className="w-12 h-12 text-white/10 mx-auto mb-4" />
                        <h3 className="text-white/60 font-medium">
                            No {type} messages configured
                        </h3>
                        <p className="text-white/40 text-sm">
                            Add your first {type} message to get started
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {messages.map((message, index) => (
                            <div key={index} className="bg-white/5 rounded-lg p-4">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <Hash className="w-4 h-4 text-white/40" />
                                        <Dropdown
                                            value={message.channel.id}
                                            onChange={(value) => {
                                                const channel = channels.find(c => c.id === value)
                                                if (!channel) return
                                                onUpdate(index, {
                                                    channel: {
                                                        id: channel.id,
                                                        name: channel.name,
                                                        type: channel.type
                                                    }
                                                })
                                            }}
                                            placeholder="Select a channel"
                                            options={channels.filter(c => c.type === "text" || c.type === "news")}
                                            className="w-full min-w-[300px]"
                                        />
                                    </div>
                                    <button
                                        onClick={() => onDelete(index)}
                                        className="p-2 hover:bg-white/5 rounded transition-colors text-white/60 hover:text-red-400"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                                <div className="space-y-4">
                                    <div className="relative">
                                        <textarea
                                            value={message.content}
                                            onChange={(e) => onUpdate(index, { content: e.target.value })}
                                            className="w-full h-24 bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white resize-none"
                                            placeholder={`Enter ${type} message content...`}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => openBuilder(message.content, (newContent) => {
                                                onUpdate(index, { content: newContent })
                                            })}
                                            className="absolute top-2 right-2 p-1 hover:bg-white/5 rounded transition-colors">
                                            <Code className="w-4 h-4 text-white/60" />
                                        </button>
                                    </div>
                                    <div>
                                        <div className="flex items-center justify-between mb-4">
                                            <div>
                                                <label className="block text-sm text-white/60">Auto-delete Message</label>
                                                <p className="text-sm text-white/40">
                                                    Automatically delete this message after a set time
                                                </p>
                                            </div>
                                            <Switch
                                                checked={message.delete_after > 0}
                                                onCheckedChange={(checked) => {
                                                    onUpdate(index, { 
                                                        delete_after: checked ? 60 : 0 
                                                    })
                                                }}
                                            />
                                        </div>
                                        {message.delete_after > 0 && (
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <input
                                                        type="number"
                                                        min="3"
                                                        max="120"
                                                        value={message.delete_after}
                                                        onChange={(e) => {
                                                            onUpdate(index, { delete_after: parseInt(e.target.value) || 0 })
                                                        }}
                                                        onBlur={(e) => {
                                                            const value = parseInt(e.target.value) || 3
                                                            const validValue = Math.min(Math.max(value, 3), 120)
                                                            onUpdate(index, { delete_after: validValue })
                                                        }}
                                                        className="w-32 px-3 py-2 bg-[#0B0C0C] border border-white/10 rounded-lg text-white"
                                                    />
                                                    <span className="text-sm text-white/60">seconds</span>
                                                </div>
                                                <p className="text-xs text-white/40">
                                                    Must be between 3 and 120 seconds
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
})

MessageSection.displayName = 'MessageSection'

export default function GreetingsPage({ params }: { params: { guildId: string } }) {
    const [localGreetings, setLocalGreetings] = useState<GreetingsResponse | null>(null)
    const [hasChanges, setHasChanges] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const { openBuilder } = useEmbedBuilder()

    const { data: greetings, isLoading } = useQuery({
        queryKey: ["greetings", params.guildId],
        queryFn: () => fetchGuildGreetings(params.guildId)
    })

    useEffect(() => {
        if (greetings && !localGreetings) {
            setLocalGreetings(greetings)
        }
    }, [greetings])

    const { data: channels } = useQuery({
        queryKey: ["channels", params.guildId],
        queryFn: () => fetchGuildChannels(params.guildId)
    })

    const handleAddWelcome = () => {
        const newMessage = {
            channel: { id: "", name: "", type: "text" },
            content: "",
            delete_after: 0
        }

        setLocalGreetings(prev =>
            prev ? {
                ...prev,
                welcome: {
                    ...prev.welcome,
                    items: [...prev.welcome.items, newMessage],
                    count: prev.welcome.count + 1
                }
            } : null
        )
        setHasChanges(true)
    }

    const handleAddGoodbye = () => {
        const newMessage = {
            channel: { id: "", name: "", type: "text" },
            content: "",
            delete_after: 0
        }

        setLocalGreetings(prev =>
            prev ? {
                ...prev,
                goodbye: {
                    ...prev.goodbye,
                    items: [...prev.goodbye.items, newMessage],
                    count: prev.goodbye.count + 1
                }
            } : null
        )
        setHasChanges(true)
    }

    const handleMessageDelete = (type: "welcome" | "goodbye") => (index: number) => {
        setLocalGreetings(prev => prev ? {
            ...prev,
            [type]: {
                ...prev[type],
                items: prev[type].items.filter((_, i) => i !== index),
                count: prev[type].count - 1
            }
        } : null)
        setHasChanges(true)
    }

    const handleSave = async () => {
        if (!localGreetings || !greetings) return
        setIsSaving(true)

        const updates: GreetingsUpdate = {
            settings: {
                welcome_removal: localGreetings.welcome.removal
            }
        }

        if (JSON.stringify(greetings.welcome.items) !== JSON.stringify(localGreetings.welcome.items)) {
            updates.welcome = []
            
            greetings.welcome.items.forEach(original => {
                if (!localGreetings.welcome.items.find(item => item.channel.id === original.channel.id)) {
                    updates.welcome?.push({
                        type: "delete",
                        channel: { id: original.channel.id }
                    })
                }
            })
            
            localGreetings.welcome.items.forEach(item => {
                const original = greetings.welcome.items.find(o => o.channel.id === item.channel.id)
                updates.welcome?.push({
                    type: original ? "edit" : "create",
                    channel: { id: item.channel.id },
                    content: item.content,
                    delete_after: item.delete_after
                })
            })
        }

        if (JSON.stringify(greetings.goodbye.items) !== JSON.stringify(localGreetings.goodbye.items)) {
            updates.goodbye = []
            
            greetings.goodbye.items.forEach(original => {
                if (!localGreetings.goodbye.items.find(item => item.channel.id === original.channel.id)) {
                    updates.goodbye?.push({
                        type: "delete",
                        channel: { id: original.channel.id }
                    })
                }
            })
            
            localGreetings.goodbye.items.forEach(item => {
                const original = greetings.goodbye.items.find(o => o.channel.id === item.channel.id)
                updates.goodbye?.push({
                    type: original ? "edit" : "create",
                    channel: { id: item.channel.id },
                    content: item.content,
                    delete_after: item.delete_after
                })
            })
        }

        try {
            await updateGuildGreetings(params.guildId, updates)
            setHasChanges(false)
            toast.success("Settings saved successfully")
        } catch (error) {
            toast.error("Failed to save settings")
        } finally {
            setIsSaving(false)
        }
    }

    if (isLoading) {
        return (
            <div className="max-w-[1920px] mx-auto space-y-6 md:space-y-8">
                <div>
                    <div className="h-8 w-48 bg-white/5 rounded-lg animate-pulse" />
                    <div className="h-4 w-96 bg-white/5 rounded-lg mt-2 animate-pulse" />
                </div>

                <div className="bg-[#141414] border border-white/5 rounded-xl p-4">
                    <div className="h-24 bg-white/5 rounded-lg animate-pulse" />
                </div>

                <div className="bg-[#141414] border border-white/5 rounded-xl p-4">
                    <div className="h-24 bg-white/5 rounded-lg animate-pulse" />
                </div>
            </div>
        )
    }

    return (
        <div className="max-w-[1920px] mx-auto space-y-6 md:space-y-8">
            <div>
                <h1 className="text-xl md:text-2xl font-bold text-white">Greetings</h1>
                <p className="text-white/60">Configure welcome and goodbye messages</p>
            </div>

            <div className="bg-[#141414] border border-white/5 rounded-xl p-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-base font-medium text-white mb-1">Auto-Remove Welcome Messages</h2>
                        <p className="text-sm text-white/60">
                            Automatically remove welcome messages if members leave shortly after joining
                        </p>
                    </div>
                    <Switch
                        checked={localGreetings?.welcome.removal ?? false}
                        onCheckedChange={(checked: boolean) => {
                            setLocalGreetings(prev => prev ? {
                                ...prev,
                                welcome: {
                                    ...prev.welcome,
                                    removal: checked
                                }
                            } : null)
                            setHasChanges(true)
                        }}
                    />
                </div>
            </div>

            <MessageSection 
                type="welcome"
                messages={localGreetings?.welcome.items || []}
                onAdd={handleAddWelcome}
                maxMessages={localGreetings?.welcome.limits.max_messages || 2}
                onUpdate={(index, updates) => {
                    setLocalGreetings(prev => prev ? {
                        ...prev,
                        welcome: {
                            ...prev.welcome,
                            items: prev.welcome.items.map((item, i) =>
                                i === index ? { ...item, ...updates } : item
                            )
                        }
                    } : null)
                    setHasChanges(true)
                }}
                onDelete={handleMessageDelete("welcome")}
                channels={channels?.channels || []}
            />

            <MessageSection 
                type="goodbye"
                messages={localGreetings?.goodbye.items || []}
                onAdd={handleAddGoodbye}
                maxMessages={localGreetings?.goodbye.limits.max_messages || 2}
                onUpdate={(index, updates) => {
                    setLocalGreetings(prev => prev ? {
                        ...prev,
                        goodbye: {
                            ...prev.goodbye,
                            items: prev.goodbye.items.map((item, i) =>
                                i === index ? { ...item, ...updates } : item
                            )
                        }
                    } : null)
                    setHasChanges(true)
                }}
                onDelete={handleMessageDelete("goodbye")}
                channels={channels?.channels || []}
            />

            <SaveButton hasChanges={hasChanges} isSaving={isSaving} onSave={handleSave} />
            <EmbedBuilder />
        </div>
    )
}
