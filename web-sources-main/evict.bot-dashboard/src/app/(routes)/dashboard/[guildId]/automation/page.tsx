"use client"

import { checkBetaAccess } from "@/libs/dashboard/beta"
import { fetchGuildChannels, fetchGuildRoles } from "@/libs/dashboard/guild"
import {
    AutomationResponse,
    AutomationUpdate,
    fetchGuildAutomation,
    updateGuildAutomation
} from "@/libs/dashboard/guild/automation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
    AtSign,
    Beaker,
    Bot,
    ChevronDown,
    ChevronUp,
    Code,
    Hash,
    Image,
    Link,
    MessageSquare,
    Plus,
    Tag,
    Trash2
} from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { toast } from "react-hot-toast"
import SaveButton from "../components/security/SaveButton"
import Dropdown from "../components/ui/Dropdown"
import { EmbedBuilder, useEmbedBuilder } from "../components/ui/EmbedBuilder"

interface Autoresponder {
    trigger: string
    content: string
    settings: {
        strict: boolean
        reply: boolean
        delete: boolean
        delete_after: number
    }
    role?: {
        id: string
        name: string
        color: number | null
    }
}

function Switch({
    checked,
    onCheckedChange
}: {
    checked: boolean
    onCheckedChange: (checked: boolean) => void
}) {
    return (
        <button
            onClick={() => onCheckedChange(!checked)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                checked ? "bg-blue-600" : "bg-white/10"
            }`}>
            <span
                className={`${
                    checked ? "translate-x-6" : "translate-x-1"
                } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
            />
        </button>
    )
}

function AutoresponderCard({
    responder: initialResponder,
    onUpdate,
    onDelete,
    roleOptions
}: {
    responder: Autoresponder
    onUpdate: (updated: Autoresponder, originalTrigger: string) => void
    onDelete: () => void
    roleOptions: { id: string; name: string; color: number }[]
}) {
    const [isExpanded, setIsExpanded] = useState(false)
    const [responder, setResponder] = useState(initialResponder)
    const { openBuilder } = useEmbedBuilder()

    const handleChange = (updates: Partial<Autoresponder>) => {
        const updated = { ...responder, ...updates }
        setResponder(updated)
        onUpdate(updated, initialResponder.trigger)
    }

    return (
        <div
            className={`bg-black/20 rounded-lg border border-white/5 ${isExpanded ? "col-span-full" : ""}`}>
            <div
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-white font-medium truncate">{responder.trigger}</span>
                        <div className="flex gap-1 flex-wrap">
                            {responder.settings.strict && (
                                <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-xs rounded-full">
                                    Strict
                                </span>
                            )}
                            {responder.settings.reply && (
                                <span className="px-2 py-0.5 bg-green-500/10 text-green-400 text-xs rounded-full">
                                    Reply
                                </span>
                            )}
                        </div>
                    </div>
                    <p className="text-white/40 text-sm line-clamp-2 break-all">
                        {responder.content}
                    </p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                    <button
                        onClick={e => {
                            e.stopPropagation()
                            onDelete()
                        }}
                        className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                        <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                    {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-white/40" />
                    ) : (
                        <ChevronDown className="w-5 h-5 text-white/40" />
                    )}
                </div>
            </div>

            {isExpanded && (
                <div className="p-4 border-t border-white/5 space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm text-white/60">Trigger</label>
                        <input
                            type="text"
                            value={responder.trigger}
                            onChange={e => handleChange({ trigger: e.target.value })}
                            className="w-full bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white"
                            placeholder="Enter trigger text"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm text-white/60">Response</label>
                        <div className="relative">
                            <textarea
                                value={responder.content}
                                onChange={e => handleChange({ content: e.target.value })}
                                className="w-full h-24 bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white resize-none"
                                placeholder="Enter response message"
                            />
                            <button
                                type="button"
                                onClick={() =>
                                    openBuilder(responder.content, newValue => {
                                        handleChange({ content: newValue })
                                    })
                                }
                                className="absolute top-2 right-2 p-1 hover:bg-white/5 rounded transition-colors">
                                <Code className="w-4 h-4 text-white/60" />
                            </button>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm text-white/60">Role</label>
                            <Dropdown
                                value={responder.role?.id ?? null}
                                onChange={value =>
                                    handleChange({
                                        role: value
                                            ? { id: value, name: "", color: null }
                                            : undefined
                                    })
                                }
                                placeholder="Select a role"
                                options={roleOptions}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm text-white/60">Delete After (seconds)</label>
                            <input
                                type="number"
                                value={responder.settings.delete_after}
                                onChange={e =>
                                    handleChange({
                                        settings: {
                                            ...responder.settings,
                                            delete_after: parseInt(e.target.value)
                                        }
                                    })
                                }
                                className="w-full bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white"
                                placeholder="Enter seconds"
                                min={1}
                            />
                        </div>
                    </div>
                    <div className="flex gap-4">
                        <label className="flex items-center gap-2">
                            <Switch
                                checked={responder.settings.strict}
                                onCheckedChange={checked =>
                                    handleChange({
                                        settings: { ...responder.settings, strict: checked }
                                    })
                                }
                            />
                            <span className="text-sm text-white/60">Strict Match</span>
                        </label>
                        <label className="flex items-center gap-2">
                            <Switch
                                checked={responder.settings.reply}
                                onCheckedChange={checked =>
                                    handleChange({
                                        settings: { ...responder.settings, reply: checked }
                                    })
                                }
                            />
                            <span className="text-sm text-white/60">Reply</span>
                        </label>
                        <label className="flex items-center gap-2">
                            <Switch
                                checked={responder.settings.delete}
                                onCheckedChange={checked =>
                                    handleChange({
                                        settings: { ...responder.settings, delete: checked }
                                    })
                                }
                            />
                            <span className="text-sm text-white/60">Delete Trigger</span>
                        </label>
                    </div>
                </div>
            )}
        </div>
    )
}

const AutoresponderCardSkeleton = () => (
    <div className="bg-black/20 rounded-lg border border-white/5">
        <div className="p-4">
            <div className="animate-pulse space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-2 flex-1">
                        <div className="bg-white/5 h-5 w-32 rounded" />
                        <div className="bg-white/5 h-4 w-64 rounded" />
                    </div>
                    <div className="bg-white/5 h-8 w-8 rounded" />
                </div>
            </div>
        </div>
    </div>
)

function TagCard({
    tag,
    onUpdate,
    onDelete
}: {
    tag: AutomationResponse["tags"]["items"][0]
    onUpdate: (updated: typeof tag) => void
    onDelete: () => void
}) {
    const [isExpanded, setIsExpanded] = useState(false)
    const { openBuilder } = useEmbedBuilder()

    return (
        <div
            className={`bg-black/20 rounded-lg border border-white/5 ${isExpanded ? "col-span-full" : ""}`}>
            <div
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-white font-medium truncate">{tag.name}</span>
                        <span className="text-white/40 text-sm">Used {tag.uses} times</span>
                    </div>
                    <p className="text-white/40 text-sm line-clamp-2 break-all">{tag.content}</p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                    <button
                        onClick={e => {
                            e.stopPropagation()
                            onDelete()
                        }}
                        className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                        <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                    {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-white/40" />
                    ) : (
                        <ChevronDown className="w-5 h-5 text-white/40" />
                    )}
                </div>
            </div>

            {isExpanded && (
                <div className="p-4 border-t border-white/5 space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm text-white/60">Name</label>
                        <input
                            type="text"
                            value={tag.name}
                            onChange={e => onUpdate({ ...tag, name: e.target.value })}
                            className="w-full bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white"
                            placeholder="Enter tag name"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm text-white/60">Content</label>
                        <div className="relative">
                            <textarea
                                value={tag.content}
                                onChange={e => onUpdate({ ...tag, content: e.target.value })}
                                className="w-full h-24 bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white resize-none"
                                placeholder="Enter tag content"
                            />
                            <button
                                type="button"
                                onClick={() =>
                                    openBuilder(tag.content, newValue => {
                                        onUpdate({ ...tag, content: newValue })
                                    })
                                }
                                className="absolute top-2 right-2 p-1 hover:bg-white/5 rounded transition-colors">
                                <Code className="w-4 h-4 text-white/60" />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

function ProfileCard({
    profile,
    onDelete
}: {
    profile: AutomationResponse["profiles"]["items"][0]
    onDelete: () => void
}) {
    return (
        <div className="bg-black/20 rounded-lg border border-white/5">
            <div className="p-4 flex items-center justify-between">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{profile.channel.name}</span>
                        <span className="px-2 py-0.5 bg-purple-500/10 text-purple-400 text-xs rounded-full capitalize">
                            {profile.type}
                        </span>
                    </div>
                    <p className="text-white/40 text-sm mt-1 capitalize">{profile.category}</p>
                </div>
                <button
                    onClick={onDelete}
                    className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                    <Trash2 className="w-4 h-4 text-red-500" />
                </button>
            </div>
        </div>
    )
}

function ReactionCard({
    reaction,
    limits,
    onUpdate,
    onDelete
}: {
    reaction: AutomationResponse["reactions"]["items"][0]
    limits: AutomationResponse["reactions"]["limits"]
    onUpdate: (updated: typeof reaction) => void
    onDelete: () => void
}) {
    const [isExpanded, setIsExpanded] = useState(false)
    const { openBuilder } = useEmbedBuilder()

    return (
        <div
            className={`bg-black/20 rounded-lg border border-white/5 ${isExpanded ? "col-span-full" : ""}`}>
            <div
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-white font-medium truncate">{reaction.trigger}</span>
                        <div className="flex gap-1">
                            {reaction.reactions.map((emoji: string, i: number) => (
                                <span key={i} className="text-sm">
                                    {emoji}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                    <button
                        onClick={e => {
                            e.stopPropagation()
                            onDelete()
                        }}
                        className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                        <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                    {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-white/40" />
                    ) : (
                        <ChevronDown className="w-5 h-5 text-white/40" />
                    )}
                </div>
            </div>

            {isExpanded && (
                <div className="p-4 border-t border-white/5 space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm text-white/60">Trigger</label>
                        <input
                            type="text"
                            value={reaction.trigger}
                            onChange={e => onUpdate({ ...reaction, trigger: e.target.value })}
                            className="w-full bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white"
                            placeholder="Enter trigger text"
                            maxLength={limits.trigger_length}
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm text-white/60">
                            Reactions (Max: {limits.max_per_trigger})
                        </label>
                        <input
                            type="text"
                            value={reaction.reactions.join(" ")}
                            onChange={e =>
                                onUpdate({
                                    ...reaction,
                                    reactions: e.target.value
                                        .split(" ")
                                        .slice(0, limits.max_per_trigger)
                                })
                            }
                            className="w-full bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white"
                            placeholder="Enter reactions (space separated)"
                        />
                    </div>
                </div>
            )}
        </div>
    )
}

export default function AutomationPage({ params }: { params: { guildId: string } }) {
    const router = useRouter()
    const queryClient = useQueryClient()
    const [hasChanges, setHasChanges] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [changes, setChanges] = useState<AutomationUpdate>({})
    const [localAutomation, setLocalAutomation] = useState<AutomationResponse | null>(null)
    const [editingVanity, setEditingVanity] = useState(false)
    const [editingUsernames, setEditingUsernames] = useState(false)

    const { data: betaAccess, isLoading: betaLoading } = useQuery({
        queryKey: ["beta"],
        queryFn: async () => {
            try {
                return await checkBetaAccess()
            } catch (err: any) {
                if (err?.status === 401) {
                    router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`)
                }
                throw err
            }
        },
        staleTime: 1000 * 60 * 15,
        retry: false
    })

    const { data: roles } = useQuery({
        queryKey: ["roles", params.guildId],
        queryFn: () => fetchGuildRoles(params.guildId),
        enabled: !!betaAccess?.has_access
    })

    const { data: channels } = useQuery({
        queryKey: ["channels", params.guildId],
        queryFn: () => fetchGuildChannels(params.guildId),
        enabled: !!betaAccess?.has_access
    })

    const { data: automation, isLoading } = useQuery({
        queryKey: ["automation", params.guildId],
        queryFn: () => fetchGuildAutomation(params.guildId),
        enabled: !!betaAccess?.has_access
    })

    useEffect(() => {
        if (automation) {
            setLocalAutomation(automation)
        }
    }, [automation])

    const handleSave = async () => {
        setIsSaving(true)
        try {
            await updateGuildAutomation(params.guildId, changes)

            queryClient.invalidateQueries({ queryKey: ["automation", params.guildId] })

            setChanges({})
            setHasChanges(false)
            toast.success("Settings saved successfully")
        } catch (error: any) {
            console.error("Save error:", error)
            toast.error("Failed to save settings")
        } finally {
            setIsSaving(false)
        }
    }

    const handleTagUpdate = (tag: AutomationResponse["tags"]["items"][0], originalName: string) => {
        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      tags: {
                          ...prev.tags,
                          items: prev.tags.items.map(t => (t.name === originalName ? tag : t))
                      }
                  }
                : null
        )

        setChanges(prev => {
            const newTags =
                prev.tags?.filter(t => t.name !== tag.name && t.name !== originalName) || []

            const isNewTag = !automation?.tags.items.some(t => t.name === originalName)

            return {
                ...prev,
                tags: [
                    ...newTags,
                    {
                        type: isNewTag ? "create" : "edit",
                        name: tag.name,
                        content: tag.content
                    }
                ]
            }
        })

        setHasChanges(true)
    }

    const handleTagDelete = (tag: AutomationResponse["tags"]["items"][0]) => {
        setChanges(prev => ({
            ...prev,
            tags: [
                ...(prev.tags || []),
                {
                    type: "delete",
                    name: tag.name
                }
            ]
        }))

        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      tags: {
                          ...prev.tags,
                          items: prev.tags.items.filter(t => t.name !== tag.name),
                          count: prev.tags.count - 1
                      }
                  }
                : null
        )

        setHasChanges(true)
    }

    const handleAutoresponderUpdate = (
        updated: AutomationResponse["autoresponses"]["items"][0],
        originalTrigger: string
    ) => {
        setChanges(prev => {
            const existingIndex =
                prev.autoresponses?.findIndex(a => a.original_trigger === originalTrigger) ?? -1

            const newAutoresponses = [...(prev.autoresponses || [])]
            const updateData = {
                type: originalTrigger === "" ? ("create" as const) : ("edit" as const),
                original_trigger: originalTrigger,
                trigger: updated.trigger,
                content: updated.content,
                settings: updated.settings
            }

            if (existingIndex >= 0) {
                newAutoresponses[existingIndex] = updateData
            } else {
                newAutoresponses.push(updateData)
            }

            return {
                ...prev,
                autoresponses: newAutoresponses
            }
        })
        setHasChanges(true)
    }

    const handleAutoresponderDelete = (
        responder: AutomationResponse["autoresponses"]["items"][0]
    ) => {
        setChanges(prev => ({
            ...prev,
            autoresponses: [
                ...(prev.autoresponses || []),
                {
                    type: "delete",
                    original_trigger: responder.trigger,
                    trigger: responder.trigger
                }
            ]
        }))

        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      autoresponses: {
                          ...prev.autoresponses,
                          items: prev.autoresponses.items.filter(
                              r => r.trigger !== responder.trigger
                          ),
                          count: prev.autoresponses.count - 1
                      }
                  }
                : null
        )

        setHasChanges(true)
    }

    const handleReactionUpdate = (
        reaction: AutomationResponse["reactions"]["items"][0],
        originalTrigger: string
    ) => {
        setChanges(prev => {
            const newReactions = [...(prev.reactions || [])]

            if (originalTrigger === "") {
                newReactions.push({
                    type: "create",
                    trigger: reaction.trigger,
                    emojis: reaction.reactions
                })
            } else {
                newReactions.push({
                    type: "edit",
                    trigger: reaction.trigger,
                    original_trigger: originalTrigger,
                    emojis: reaction.reactions
                } as any)
            }

            return {
                ...prev,
                reactions: newReactions
            }
        })
        setHasChanges(true)
    }

    const handleReactionDelete = (reaction: AutomationResponse["reactions"]["items"][0]) => {
        setChanges(prev => ({
            ...prev,
            reactions: [
                ...(prev.reactions || []),
                {
                    type: "delete",
                    trigger: reaction.trigger
                }
            ]
        }))

        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      reactions: {
                          ...prev.reactions,
                          items: prev.reactions.items.filter(r => r.trigger !== reaction.trigger),
                          count: prev.reactions.count - 1
                      }
                  }
                : null
        )

        setHasChanges(true)
    }

    const handleAddAutoresponder = () => {
        const newResponder = {
            trigger: "",
            content: "",
            settings: {
                strict: false,
                reply: false,
                delete: false,
                delete_after: 0
            }
        }

        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      autoresponses: {
                          ...prev.autoresponses,
                          items: [...prev.autoresponses.items, newResponder],
                          count: prev.autoresponses.count + 1
                      }
                  }
                : null
        )

        setChanges(prev => ({
            ...prev,
            autoresponses: [
                ...(prev.autoresponses || []),
                {
                    type: "create",
                    original_trigger: newResponder.trigger,
                    trigger: newResponder.trigger,
                    content: newResponder.content,
                    settings: newResponder.settings
                }
            ]
        }))

        setHasChanges(true)
    }

    const handleAddProfile = (profile: AutomationResponse["profiles"]["items"][0]) => {
        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      profiles: {
                          ...prev.profiles,
                          items: [...prev.profiles.items, profile],
                          count: prev.profiles.count + 1
                      }
                  }
                : null
        )

        setChanges(prev => ({
            ...prev,
            profiles: [
                ...(prev.profiles || []),
                {
                    type: "create",
                    channel: { id: profile.channel.id },
                    media_type: profile.type,
                    category: profile.category
                }
            ]
        }))
        setHasChanges(true)
    }

    const handleProfileDelete = (profile: AutomationResponse["profiles"]["items"][0]) => {
        setChanges(prev => ({
            ...prev,
            profiles: [
                ...(prev.profiles || []),
                {
                    type: "delete",
                    channel: { id: profile.channel.id },
                    media_type: profile.type
                }
            ]
        }))

        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      profiles: {
                          ...prev.profiles,
                          items: prev.profiles.items.filter(
                              p => !(p.channel.id === profile.channel.id && p.type === profile.type)
                          ),
                          count: prev.profiles.count - 1
                      }
                  }
                : null
        )

        setHasChanges(true)
    }

    const handleVanityTrackerUpdate = (channelId: string | null) => {
        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      trackers: {
                          ...prev.trackers,
                          vanity: {
                              channel: channelId
                                  ? {
                                        id: channelId,
                                        name:
                                            channels?.channels.find(c => c.id === channelId)
                                                ?.name || "",
                                        type:
                                            channels?.channels.find(c => c.id === channelId)
                                                ?.type || ""
                                    }
                                  : { id: "", name: "", type: "" }
                          }
                      }
                  }
                : null
        )

        setChanges(prev => ({
            ...prev,
            trackers: {
                ...prev.trackers,
                vanity: channelId ? { channel: { id: channelId } } : null
            }
        }))
        setHasChanges(true)
    }

    const handleUsernameTrackerUpdate = (channelId: string | null) => {
        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      trackers: {
                          ...prev.trackers,
                          usernames: {
                              channel: channelId
                                  ? {
                                        id: channelId,
                                        name:
                                            channels?.channels.find(c => c.id === channelId)
                                                ?.name || "",
                                        type:
                                            channels?.channels.find(c => c.id === channelId)
                                                ?.type || ""
                                    }
                                  : { id: "", name: "", type: "" }
                          }
                      }
                  }
                : null
        )

        setChanges(prev => ({
            ...prev,
            trackers: {
                ...prev.trackers,
                usernames: channelId ? { channel: { id: channelId } } : null
            }
        }))
        setHasChanges(true)
    }

    const handleAddReaction = () => {
        const newReaction = {
            trigger: "",
            reactions: [],
            uses: 0
        }

        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      reactions: {
                          ...prev.reactions,
                          items: [...prev.reactions.items, newReaction],
                          count: prev.reactions.count + 1
                      }
                  }
                : null
        )

        setChanges(prev => ({
            ...prev,
            reactions: [
                ...(prev.reactions || []),
                {
                    type: "create",
                    trigger: newReaction.trigger,
                    emojis: newReaction.reactions
                }
            ]
        }))

        setHasChanges(true)
    }

    const handleAddTag = () => {
        const newTag = {
            name: "",
            content: "",
            uses: 0,
            owner_id: "",
            created_at: new Date().toISOString(),
            aliases: []
        }

        setLocalAutomation(prev =>
            prev
                ? {
                      ...prev,
                      tags: {
                          ...prev.tags,
                          items: [...prev.tags.items, newTag],
                          count: prev.tags.count + 1
                      }
                  }
                : null
        )

        setChanges(prev => ({
            ...prev,
            tags: [
                ...(prev.tags || []),
                {
                    type: "create",
                    name: newTag.name,
                    content: newTag.content
                }
            ]
        }))

        setHasChanges(true)
    }

    if (!betaLoading && !betaAccess?.has_access) {
        return (
            <div className="fixed inset-0 flex flex-col items-center justify-center text-center bg-[#0B0C0C] z-50">
                <div className="bg-blue-500/10 p-2 rounded-full mb-4">
                    <Beaker className="w-8 h-8 text-blue-500" />
                </div>
                <h1 className="text-2xl font-bold text-white mb-2">Beta Access Required</h1>
                <p className="text-white/60 max-w-md">
                    This feature is currently in beta. Join our Discord server to request access.
                </p>
            </div>
        )
    }

    if (isLoading) {
        return (
            <div className="max-w-[1920px] mx-auto space-y-6 md:space-y-8">
                <div className="animate-pulse space-y-2">
                    <div className="bg-white/5 h-8 w-32 rounded" />
                    <div className="bg-white/5 h-5 w-64 rounded" />
                </div>

                <div className="bg-[#141414] border border-white/5 rounded-xl">
                    <div className="p-4 border-b border-white/5">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="bg-white/5 h-5 w-5 rounded" />
                                <div className="bg-white/5 h-5 w-32 rounded" />
                            </div>
                            <div className="bg-white/5 h-9 w-32 rounded-lg" />
                        </div>
                    </div>

                    <div className="p-4 space-y-2">
                        {[...Array(3)].map((_, i) => (
                            <AutoresponderCardSkeleton key={i} />
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="max-w-[1920px] mx-auto space-y-6 md:space-y-8">
            <div>
                <h1 className="text-xl md:text-2xl font-bold text-white">Automation</h1>
                <p className="text-white/60">Configure automated responses and actions</p>
            </div>

            {/* Tags Section */}
            <div className="bg-[#141414] border border-white/5 rounded-xl">
                <div className="p-4 border-b border-white/5">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Tag className="w-5 h-5 text-white/60" />
                            <h2 className="text-base font-medium text-white">
                                Tags ({automation?.tags.count ?? 0})
                            </h2>
                        </div>
                        <button
                            onClick={handleAddTag}
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                            <Plus className="w-4 h-4" />
                            Add Tag
                        </button>
                    </div>
                </div>

                <div className="p-4">
                    {localAutomation?.tags.items.length === 0 ? (
                        <div className="text-center py-12">
                            <Tag className="w-12 h-12 text-white/10 mx-auto mb-4" />
                            <h3 className="text-white/60 font-medium">No tags configured</h3>
                            <p className="text-white/40 text-sm">
                                Add your first tag to get started
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                            {localAutomation?.tags.items.map((tag, index) => (
                                <TagCard
                                    key={`tag-${index}`}
                                    tag={tag}
                                    onUpdate={updated => handleTagUpdate(updated, tag.name)}
                                    onDelete={() => handleTagDelete(tag)}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="bg-[#141414] border border-white/5 rounded-xl">
                <div className="p-4 border-b border-white/5">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <MessageSquare className="w-5 h-5 text-white/60" />
                            <h2 className="text-base font-medium text-white">
                                Responders (
                                {(automation?.autoresponses.count ?? 0) +
                                    (automation?.reactions.count ?? 0)}
                                )
                            </h2>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => handleAddReaction()}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                                <Plus className="w-4 h-4" />
                                Add Reaction
                            </button>
                            <button
                                onClick={handleAddAutoresponder}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                                <Plus className="w-4 h-4" />
                                Add Response
                            </button>
                        </div>
                    </div>
                </div>

                <div className="p-4 space-y-2">
                    {automation?.autoresponses.items.length === 0 &&
                    automation?.reactions.items.length === 0 ? (
                        <div className="text-center py-12">
                            <Bot className="w-12 h-12 text-white/10 mx-auto mb-4" />
                            <h3 className="text-white/60 font-medium">No automation configured</h3>
                            <p className="text-white/40 text-sm">
                                Add your first automation to get started
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                            {localAutomation?.reactions.items.map(reaction => (
                                <ReactionCard
                                    key={reaction.trigger || "new-reaction"}
                                    reaction={reaction}
                                    limits={automation?.reactions.limits!}
                                    onUpdate={updated =>
                                        handleReactionUpdate(updated, reaction.trigger)
                                    }
                                    onDelete={() => handleReactionDelete(reaction)}
                                />
                            ))}
                            {localAutomation?.autoresponses.items.map(responder => (
                                <AutoresponderCard
                                    key={responder.trigger || "new-responder"}
                                    responder={responder}
                                    onUpdate={handleAutoresponderUpdate}
                                    onDelete={() => handleAutoresponderDelete(responder)}
                                    roleOptions={roles?.roles ?? []}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="bg-[#141414] border border-white/5 rounded-xl">
                <div className="p-4 border-b border-white/5">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Image className="w-5 h-5 text-white/60" />
                            <h2 className="text-base font-medium text-white">
                                Profiles ({automation?.profiles.count ?? 0})
                            </h2>
                        </div>
                        <button
                            onClick={() =>
                                handleAddProfile({
                                    channel: { id: "", name: "", type: "" },
                                    type: "pfp",
                                    category: "random"
                                })
                            }
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                            <Plus className="w-4 h-4" />
                            Add Profile
                        </button>
                    </div>
                </div>

                <div className="p-4 space-y-2">
                    {automation?.profiles.items.length === 0 ? (
                        <div className="text-center py-12">
                            <Image className="w-12 h-12 text-white/10 mx-auto mb-4" />
                            <h3 className="text-white/60 font-medium">No profiles configured</h3>
                            <p className="text-white/40 text-sm">
                                Add your first profile to get started
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                            {automation?.profiles.items.map((profile, index) => (
                                <ProfileCard
                                    key={index}
                                    profile={profile}
                                    onDelete={() => handleProfileDelete(profile)}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-[#141414] border border-white/5 rounded-xl">
                    <div className="p-4 border-b border-white/5">
                        <div className="flex items-center gap-3">
                            <AtSign className="w-5 h-5 text-white/60" />
                            <h2 className="text-base font-medium text-white">Username Tracker</h2>
                        </div>
                    </div>
                    <div className="p-4 w-full">
                        <div className="flex items-center justify-between">
                            {editingUsernames ? (
                                <Dropdown
                                    value={localAutomation?.trackers.usernames.channel.id ?? null}
                                    onChange={handleUsernameTrackerUpdate}
                                    options={
                                        channels?.channels
                                            .filter(c => c.type === "text" || c.type === "news")
                                            .map(c => ({ id: c.id, name: c.name })) ?? []
                                    }
                                    placeholder="Select channel"
                                    className="w-full min-w-[300px]"
                                    searchable
                                />
                            ) : (
                                <>
                                    <div>
                                        <p className="text-white/60 text-sm mb-2">Channel</p>
                                        <div className="flex items-center gap-2">
                                            <Hash className="w-4 h-4 text-white/40" />
                                            <span className="text-white">
                                                {localAutomation?.trackers.usernames.channel.name}
                                            </span>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setEditingUsernames(true)}
                                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                                        Edit Channel
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </div>

                <div className="bg-[#141414] border border-white/5 rounded-xl">
                    <div className="p-4 border-b border-white/5">
                        <div className="flex items-center gap-3">
                            <Link className="w-5 h-5 text-white/60" />
                            <h2 className="text-base font-medium text-white">Vanity Tracker</h2>
                        </div>
                    </div>
                    <div className="p-4">
                        <div className="flex items-center justify-between">
                            {editingVanity ? (
                                <Dropdown
                                    value={localAutomation?.trackers.vanity.channel.id ?? null}
                                    onChange={handleVanityTrackerUpdate}
                                    options={
                                        channels?.channels
                                            .filter(c => c.type === "text")
                                            .map(c => ({ id: c.id, name: c.name })) ?? []
                                    }
                                    placeholder="Select channel"
                                    className="w-full"
                                />
                            ) : (
                                <>
                                    <div>
                                        <p className="text-white/60 text-sm mb-2">Channel</p>
                                        <div className="flex items-center gap-2">
                                            <Hash className="w-4 h-4 text-white/40" />
                                            <span className="text-white">
                                                {localAutomation?.trackers.vanity.channel.name}
                                            </span>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setEditingVanity(true)}
                                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                                        Edit Channel
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <SaveButton hasChanges={hasChanges} isSaving={isSaving} onSave={handleSave} />
            <EmbedBuilder />
        </div>
    )
}
