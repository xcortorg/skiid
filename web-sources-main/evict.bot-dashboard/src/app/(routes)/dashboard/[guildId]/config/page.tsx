"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchGuildConfig, updateGuildConfig, ConfigRequest } from "@/libs/dashboard/guild/config"
import { fetchGuildRoles, fetchGuildChannels } from "@/libs/dashboard/guild"
import { checkBetaAccess } from "@/libs/dashboard/beta"

import { useParams, useRouter } from "next/navigation"
import { Settings, Shield, Bell, MessageSquare, Users, Link, Code, Beaker, UserPlus, ShieldAlert, X, Plus } from "lucide-react"
import { useState, useEffect } from "react"
import SaveButton from "../components/security/SaveButton"
import ProtectionSettings from "../components/security/ProtectionSettings"
import { ConfigResponse } from "@/libs/dashboard/guild/config"
import Dropdown from "../components/ui/Dropdown"
import { EmbedBuilder, useEmbedBuilder } from "../components/ui/EmbedBuilder"
import toast from 'react-hot-toast'
import { useQueryClient } from "@tanstack/react-query"
import { fetchGuildModLogs } from "@/libs/dashboard/guild/modlogs"
import { fetchGuildLogging } from "@/libs/dashboard/guild/logging"
import { Dialog } from "@headlessui/react"

function BetaAccessRequired() {
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

const CommandDialog = ({ 
    open, 
    onClose, 
    onAdd,
    roleOptions 
}: { 
    open: boolean
    onClose: () => void
    onAdd: (command: string, roleId: string) => void
    roleOptions: { id: string; name: string; color: number }[]
}) => {
    const [command, setCommand] = useState("")
    const [selectedRole, setSelectedRole] = useState<string>("")

    return (
        <Dialog
            open={open}
            onClose={onClose}
            className="relative z-50"
        >
            <div className="fixed inset-0 bg-black/50" aria-hidden="true" />

            <div className="fixed inset-0 flex items-center justify-center p-4">
                <Dialog.Panel className="relative bg-[#0B0C0C] p-6 rounded-xl border border-[#222222] w-[95vw] max-w-[500px]">
                    <button 
                        onClick={onClose}
                        className="absolute top-4 right-4 hover:bg-white/5 p-1 rounded transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                    <Dialog.Title className="text-lg font-semibold mb-4">
                        Add Command Restriction
                    </Dialog.Title>

                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm text-white/60">Command Name</label>
                            <input
                                type="text"
                                value={command}
                                onChange={(e) => setCommand(e.target.value.toLowerCase())}
                                placeholder="Enter command name"
                                className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2 text-white"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm text-white/60">Required Role</label>
                            <Dropdown
                                value={selectedRole}
                                onChange={setSelectedRole}
                                placeholder="Select a role"
                                options={roleOptions}
                            />
                        </div>
                        <div className="flex justify-end">
                            <button
                                onClick={() => {
                                    if (command.trim() && selectedRole) {
                                        onAdd(command.trim(), selectedRole)
                                        setCommand("")
                                        setSelectedRole("")
                                    }
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-[#0B0C0C] text-white rounded-xl border border-[#222222] hover:bg-[#151515] transition-colors"
                            >
                                <Plus className="w-4 h-4" />
                                <span>Add Command</span>
                            </button>
                        </div>
                    </div>
                </Dialog.Panel>
            </div>
        </Dialog>
    )
}

const BlacklistDialog = ({ 
    open, 
    onClose, 
    onAdd 
}: { 
    open: boolean
    onClose: () => void
    onAdd: (word: string) => void 
}) => {
    const [word, setWord] = useState("")

    return (
        <Dialog
            open={open}
            onClose={onClose}
            className="relative z-50"
        >
            <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
            <div className="fixed inset-0 flex items-center justify-center p-4">
                <Dialog.Panel className="relative bg-[#0B0C0C] p-6 rounded-xl border border-[#222222] w-[95vw] max-w-[500px]">
                    <button onClick={onClose} className="absolute top-4 right-4 hover:bg-white/5 p-1 rounded transition-colors">
                        <X className="w-4 h-4" />
                    </button>
                    <Dialog.Title className="text-lg font-semibold mb-4">Add Blacklisted Word</Dialog.Title>
                    <div className="space-y-4">
                        <input
                            type="text"
                            value={word}
                            onChange={(e) => setWord(e.target.value.toLowerCase())}
                            placeholder="Enter word to blacklist"
                            className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2 text-white"
                        />
                        <div className="flex justify-end">
                            <button
                                onClick={() => {
                                    if (word.trim()) {
                                        onAdd(word.trim())
                                        setWord("")
                                        onClose()
                                    }
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-[#0B0C0C] text-white rounded-xl border border-[#222222] hover:bg-[#151515] transition-colors"
                            >
                                Add Word
                            </button>
                        </div>
                    </div>
                </Dialog.Panel>
            </div>
        </Dialog>
    )
}

const MuteUserDialog = ({ 
    open, 
    onClose, 
    onAdd 
}: { 
    open: boolean
    onClose: () => void
    onAdd: (userId: string) => void 
}) => {
    const [userId, setUserId] = useState("")

    return (
        <Dialog
            open={open}
            onClose={onClose}
            className="relative z-50"
        >
            <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
            <div className="fixed inset-0 flex items-center justify-center p-4">
                <Dialog.Panel className="relative bg-[#0B0C0C] p-6 rounded-xl border border-[#222222] w-[95vw] max-w-[500px]">
                    <button onClick={onClose} className="absolute top-4 right-4 hover:bg-white/5 p-1 rounded transition-colors">
                        <X className="w-4 h-4" />
                    </button>
                    <Dialog.Title className="text-lg font-semibold mb-4">Mute User</Dialog.Title>
                    <div className="space-y-4">
                        <input
                            type="text"
                            value={userId}
                            onChange={(e) => setUserId(e.target.value)}
                            placeholder="Enter user ID"
                            className="w-full bg-[#0B0C0C] border border-[#222222] rounded-xl px-3 py-2 text-white"
                        />
                        <div className="flex justify-end">
                            <button
                                onClick={() => {
                                    if (userId.trim()) {
                                        onAdd(userId.trim())
                                        setUserId("")
                                        onClose()
                                    }
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-[#0B0C0C] text-white rounded-xl border border-[#222222] hover:bg-[#151515] transition-colors"
                            >
                                Mute User
                            </button>
                        </div>
                    </div>
                </Dialog.Panel>
            </div>
        </Dialog>
    )
}

export default function ConfigPage() {
    const params = useParams<{ guildId: string }>()
    const [hasChanges, setHasChanges] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [settings, setSettings] = useState<ConfigResponse | null>(null)
    const router = useRouter()
    const queryClient = useQueryClient()
    const [showCommandDialog, setShowCommandDialog] = useState(false)
    const [showBlacklistDialog, setShowBlacklistDialog] = useState(false)
    const [showMuteDialog, setShowMuteDialog] = useState(false)

    useEffect(() => {
        queryClient.prefetchQuery({
            queryKey: ["modlogs", params.guildId],
            queryFn: () => fetchGuildModLogs(params.guildId)
        })
        queryClient.prefetchQuery({
            queryKey: ["logs", params.guildId],
            queryFn: () => fetchGuildLogging(params.guildId)
        })
    }, [params.guildId, queryClient])

    const { data: betaAccess } = useQuery({
        queryKey: ["beta"],
        queryFn: checkBetaAccess,
        staleTime: Infinity 
    })

    const { data: config } = useQuery({
        queryKey: ["config", params.guildId],
        queryFn: () => fetchGuildConfig(params.guildId),
        enabled: !!betaAccess?.has_access,
        staleTime: 1000 * 60 * 5,
        placeholderData: (prev) => prev
    })

    const { data: roles } = useQuery({
        queryKey: ["roles", params.guildId],
        queryFn: () => fetchGuildRoles(params.guildId),
        staleTime: Infinity, 
        placeholderData: (prev) => prev
    })

    const { data: channels } = useQuery({
        queryKey: ["channels", params.guildId],
        queryFn: () => fetchGuildChannels(params.guildId),
        staleTime: Infinity, 
        placeholderData: (prev) => prev
    })

    const { openBuilder } = useEmbedBuilder()

    useEffect(() => {
        if (betaAccess && !betaAccess.has_access) {
            const currentPath = window.location.pathname
            router.push(`/login?redirect=${encodeURIComponent(currentPath)}&forBeta=true`)
        }
    }, [betaAccess, router])

    useEffect(() => {
        if (!settings && config) {
            setSettings(config)
        }
    }, [config, settings])

    useEffect(() => {
        if (config && settings) {
            const cleanConfig = JSON.parse(JSON.stringify(config))
            const cleanSettings = JSON.parse(JSON.stringify(settings))

            const isEqual = JSON.stringify(cleanConfig) === JSON.stringify(cleanSettings)
            setHasChanges(!isEqual)
        }
    }, [config, settings])

    const updateSettings = (newSettings: Partial<ConfigResponse>) => {
        setSettings(prev => {
            if (!prev) return null
            
            const updated = {
                ...prev,
                ...newSettings
            }
            
            const isEqual = JSON.stringify(config) === JSON.stringify(updated)
            setHasChanges(!isEqual)
            
            return updated
        })
    }

    const handleSave = async () => {
        if (!settings) return;
        
        setIsSaving(true)
        try {
            const updatedConfig: ConfigRequest = {
                prefix: settings.prefix,
                moderation: {
                    dm_notifications: {
                        ...settings.moderation.dm_notifications,
                        invoke_messages: settings.moderation.dm_notifications.invoke_messages
                    }
                },
                whitelist: settings.moderation.whitelist,
                vanity: settings.moderation.vanity,
                confessions: {
                    enabled: settings.confessions?.enabled ?? false,
                    channel_id: settings.confessions?.channel_id ?? null,
                    reactions: {
                        upvote: settings.confessions?.reactions.upvote ?? "👍",
                        downvote: settings.confessions?.reactions.downvote ?? "👎"
                    },
                    blacklisted_words: settings.confessions?.blacklisted_words ?? [],
                    muted_users: settings.confessions?.muted_users ?? []
                },
                join_dm: {
                    enabled: settings.join_dm?.enabled ?? false,
                    message: settings.join_dm?.message ?? ""
                },
                restricted_commands: settings.restricted_commands ?? {}
            }

            await updateGuildConfig(params.guildId, updatedConfig)
            
            queryClient.setQueryData(["config", params.guildId], settings)
            
            setHasChanges(false)
            toast.success('Settings saved successfully')
        } catch (error) {
            toast.error('Failed to save settings')
            console.error('Failed to save:', error)
        } finally {
            setIsSaving(false)
        }
    }

    const formatActionName = (action: string) => {
        return action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    };

    const roleOptions = roles?.roles
        .sort((a, b) => b.position - a.position)
        .map(role => ({
            id: role.id,
            name: role.name,
            color: role.color
        })) ?? [];

    const channelOptions = channels?.channels
        .filter(channel => 
            (channel.type === 'text' || channel.type === 'news') && 
            !channel.name.startsWith('ticket-')
        )
        .sort((a, b) => a.position - b.position)
        .map(channel => ({
            id: channel.id,
            name: `# ${channel.name}`,
            category: false
        })) ?? [];

    if (!betaAccess?.has_access) {
        return <BetaAccessRequired />
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-xl md:text-2xl font-bold text-white">Configuration</h1>
                <p className="text-white/60">Manage your server&apos;s bot settings</p>
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Settings className="w-5 h-5 text-white/60" />
                    <h2 className="text-base font-medium text-white">General Settings</h2>
                </div>
                <div className="space-y-4">
                    <div className="space-y-4">
                        <div className="flex items-center gap-2">
                            <label className="text-sm text-white/60">Command Prefix</label>
                            <input 
                                type="text" 
                                value={settings?.prefix ?? ''} 
                                onChange={(e) => updateSettings({ prefix: e.target.value })}
                                className="w-16 bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-1.5 text-white text-sm"
                                maxLength={3}
                                placeholder="!"
                            />
                        </div>
                    </div>
                </div>
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Shield className="w-5 h-5 text-white/60" />
                    <h2 className="text-base font-medium text-white">Moderation</h2>
                </div>
                <div className="space-y-6">
                    <ProtectionSettings
                        title="Enable Moderation"
                        description="Enable moderation features for your server"
                        enabled={settings?.moderation.enabled ?? false}
                        onToggle={(enabled) => updateSettings({
                            moderation: { 
                                ...settings?.moderation!,
                                enabled
                            }
                        })}
                    />

                    {settings?.moderation.enabled && (
                        <div className="space-y-6 pl-6 border-l border-white/10">
                            <div className="space-y-4">
                                <div className="flex items-center gap-3 mb-4">
                                    <Bell className="w-4 h-4 text-white/60" />
                                    <h3 className="text-sm font-medium text-white">DM Notifications</h3>
                                </div>
                                <ProtectionSettings
                                    title="Send DM on Action"
                                    description="Send a DM to users when moderation actions are taken"
                                    enabled={settings?.moderation.dm_notifications?.enabled ?? false}
                                    onToggle={(enabled) => updateSettings({
                                        moderation: { 
                                            ...settings?.moderation!,
                                            dm_notifications: {
                                                ...settings?.moderation.dm_notifications!,
                                                enabled
                                            }
                                        }
                                    })}
                                />

                                {settings?.moderation.dm_notifications?.enabled && (
                                    <div className="space-y-6 mt-4">
                                        <div className="grid gap-4 md:grid-cols-2">
                                            {Object.entries(settings?.moderation.dm_notifications?.actions ?? {}).map(([action, enabled]) => (
                                                <ProtectionSettings
                                                    key={action}
                                                    title={formatActionName(action)}
                                                    description={`Send DM on ${formatActionName(action).toLowerCase()}`}
                                                    enabled={enabled}
                                                    onToggle={(newEnabled) => updateSettings({
                                                        moderation: { 
                                                            ...settings?.moderation!,
                                                            dm_notifications: {
                                                                ...settings?.moderation.dm_notifications!,
                                                                actions: {
                                                                    ...settings?.moderation.dm_notifications?.actions!,
                                                                    [action]: newEnabled
                                                                }
                                                            }
                                                        }
                                                    })}
                                                />
                                            ))}
                                        </div>

                                        <div className="space-y-4">
                                            <div className="flex items-center gap-3 mb-4">
                                                <MessageSquare className="w-4 h-4 text-white/60" />
                                                <h4 className="text-sm font-medium text-white">Custom DM Messages</h4>
                                            </div>
                                            <div className="grid gap-4 md:grid-cols-2">
                                                {Object.entries(settings?.moderation.dm_notifications?.messages ?? {}).map(([action, message]) => (
                                                    <div key={action} className="space-y-2">
                                                        <label className="text-sm text-white/60 capitalize">{formatActionName(action)} Message</label>
                                                        <div className="relative">
                                                            <textarea 
                                                                value={message} 
                                                                onChange={(e) => updateSettings({
                                                                    moderation: { 
                                                                        ...settings?.moderation!,
                                                                        dm_notifications: {
                                                                            ...settings?.moderation.dm_notifications!,
                                                                            messages: {
                                                                                ...settings?.moderation.dm_notifications?.messages!,
                                                                                [action]: e.target.value
                                                                            }
                                                                        }
                                                                    }
                                                                })}
                                                                placeholder={`Custom message for ${formatActionName(action)}`}
                                                                className="w-full h-24 bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white resize-none"
                                                            />
                                                            <button
                                                                type="button"
                                                                onClick={() => openBuilder(message, (newValue: string) => {
                                                                    updateSettings({
                                                                        moderation: { 
                                                                            ...settings?.moderation!,
                                                                            dm_notifications: {
                                                                                ...settings?.moderation.dm_notifications!,
                                                                                messages: {
                                                                                    ...settings?.moderation.dm_notifications?.messages!,
                                                                                    [action]: newValue
                                                                                }
                                                                            }
                                                                        }
                                                                    })
                                                                })}
                                                                className="absolute top-2 right-2 p-1 hover:bg-white/5 rounded transition-colors"
                                                            >
                                                                <Code className="w-4 h-4 text-white/60" />
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center gap-3 mb-4">
                                    <MessageSquare className="w-4 h-4 text-white/60" />
                                    <h3 className="text-sm font-medium text-white">Invoke Messages</h3>
                                </div>
                                <div className="grid gap-4 md:grid-cols-2">
                                    {Object.entries(settings?.moderation.dm_notifications.invoke_messages ?? {}).map(([action, data]) => (
                                        <div key={action} className="space-y-2">
                                            <div className="flex items-center justify-between">
                                                <label className="text-sm text-white/60 capitalize">{formatActionName(action)} Message</label>
                                                <ProtectionSettings
                                                    title=""
                                                    description=""
                                                    enabled={data.enabled}
                                                    onToggle={(enabled) => updateSettings({
                                                        moderation: {
                                                            ...settings?.moderation!,
                                                            dm_notifications: {
                                                                ...settings?.moderation.dm_notifications!,
                                                                invoke_messages: {
                                                                    ...settings?.moderation.dm_notifications.invoke_messages!,
                                                                    [action]: {
                                                                        ...data,
                                                                        enabled
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    })}
                                                />
                                            </div>
                                            <div className="relative">
                                                <textarea 
                                                    value={data.message}
                                                    onChange={(e) => updateSettings({
                                                        moderation: {
                                                            ...settings?.moderation!,
                                                            dm_notifications: {
                                                                ...settings?.moderation.dm_notifications!,
                                                                invoke_messages: {
                                                                    ...settings?.moderation.dm_notifications.invoke_messages!,
                                                                    [action]: {
                                                                        ...data,
                                                                        message: e.target.value
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    })}
                                                    placeholder={`Custom message for ${formatActionName(action)}`}
                                                    className="w-full h-24 bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white resize-none"
                                                />
                                                <button
                                                    type="button"
                                                    onClick={() => openBuilder(data.message, (newValue) => {
                                                        updateSettings({
                                                            moderation: {
                                                                ...settings?.moderation!,
                                                                dm_notifications: {
                                                                    ...settings?.moderation.dm_notifications!,
                                                                    invoke_messages: {
                                                                        ...settings?.moderation.dm_notifications.invoke_messages!,
                                                                        [action]: {
                                                                            ...data,
                                                                            message: newValue
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        })
                                                    })}
                                                    className="absolute top-2 right-2 p-1 hover:bg-white/5 rounded transition-colors"
                                                >
                                                    <Code className="w-4 h-4 text-white/60" />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Users className="w-5 h-5 text-white/60" />
                    <h2 className="text-base font-medium text-white">Whitelist</h2>
                </div>
                <div className="space-y-6">
                    <ProtectionSettings
                        title="Enable Whitelist"
                        description="Only allow whitelisted users to join"
                        enabled={settings?.moderation.whitelist.enabled ?? false}
                        onToggle={(enabled) => updateSettings({
                            moderation: {
                                ...settings?.moderation!,
                                whitelist: {
                                    ...settings?.moderation.whitelist!,
                                    enabled
                                }
                            }
                        })}
                    />
                    {settings?.moderation.whitelist.enabled && (
                        <div className="space-y-4 pl-6 border-l border-white/10">
                            <div className="flex items-center gap-2">
                                <label className="text-sm text-white/60">Action</label>
                                <select
                                    value={settings?.moderation.whitelist.action}
                                    onChange={(e) => updateSettings({
                                        moderation: {
                                            ...settings?.moderation!,
                                            whitelist: {
                                                ...settings?.moderation.whitelist!,
                                                action: e.target.value as "kick" | "ban"
                                            }
                                        }
                                    })}
                                    className="bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                                >
                                    <option value="kick">Kick</option>
                                    <option value="ban">Ban</option>
                                </select>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Link className="w-5 h-5 text-white/60" />
                    <h2 className="text-base font-medium text-white">Vanity</h2>
                </div>
                <div className="space-y-6">
                    <ProtectionSettings
                        title="Enable Vanity"
                        description="Custom vanity URL system"
                        enabled={settings?.moderation.vanity.enabled ?? false}
                        onToggle={(enabled) => updateSettings({
                            moderation: {
                                ...settings?.moderation!,
                                vanity: {
                                    ...settings?.moderation.vanity!,
                                    enabled
                                }
                            }
                        })}
                    />
                    {settings?.moderation.vanity.enabled && (
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm text-white/60">Role</label>
                                <Dropdown
                                    value={settings.moderation.vanity.role_id}
                                    onChange={(value) => updateSettings({
                                        moderation: {
                                            ...settings.moderation,
                                            vanity: {
                                                ...settings.moderation.vanity,
                                                role_id: value || null
                                            }
                                        }
                                    })}
                                    placeholder="Select a role"
                                    options={roleOptions}
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm text-white/60">Channel</label>
                                <Dropdown
                                    value={settings.moderation.vanity.channel_id}
                                    onChange={(value) => updateSettings({
                                        moderation: {
                                            ...settings.moderation,
                                            vanity: {
                                                ...settings.moderation.vanity,
                                                channel_id: value || null
                                            }
                                        }
                                    })}
                                    placeholder="Select a channel"
                                    options={channelOptions}
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm text-white/60">Template</label>
                                <div className="relative">
                                    <textarea 
                                        value={settings.moderation.vanity.template ?? settings.moderation.vanity.default_template}
                                        onChange={(e) => updateSettings({
                                            moderation: {
                                                ...settings.moderation,
                                                vanity: {
                                                    ...settings.moderation.vanity,
                                                    template: e.target.value
                                                }
                                            }
                                        })}
                                        placeholder="Custom vanity template"
                                        className="w-full h-24 bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white resize-none text-sm"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => openBuilder(settings.moderation.vanity.template ?? settings.moderation.vanity.default_template, (newValue) => {
                                            updateSettings({
                                                moderation: {
                                                    ...settings.moderation,
                                                    vanity: {
                                                        ...settings.moderation.vanity,
                                                        template: newValue
                                                    }
                                                }
                                            })
                                        })}
                                        className="absolute top-2 right-2 p-1 hover:bg-white/5 rounded transition-colors"
                                    >
                                        <Code className="w-4 h-4 text-white/60" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {settings?.confessions && (
                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                        <MessageSquare className="w-5 h-5 text-white/60" />
                        <h2 className="text-base font-medium text-white">Confessions</h2>
                    </div>
                    <div className="space-y-6">
                        <ProtectionSettings
                            title="Enable Confessions"
                            description="Allow users to submit anonymous confessions"
                            enabled={settings!.confessions!.enabled}
                            onToggle={(enabled) => updateSettings({
                                confessions: {
                                    ...settings!.confessions!,
                                    enabled
                                }
                            })}
                        />
                        {settings.confessions.enabled && (
                            <div className="space-y-4 pl-6 border-l border-white/10">
                                <div className="space-y-2">
                                    <label className="text-sm text-white/60">Confession Channel</label>
                                    <Dropdown
                                        value={settings.confessions.channel_id ?? ""}
                                        onChange={(value) => updateSettings({
                                            confessions: {
                                                ...settings!.confessions!,
                                                channel_id: value
                                            }
                                        })}
                                        placeholder="Select a channel"
                                        options={channelOptions}
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <label className="text-sm text-white/60">Upvote Reaction</label>
                                        <input 
                                            type="text"
                                            value={settings.confessions.reactions.upvote}
                                            onChange={(e) => updateSettings({
                                                confessions: {
                                                    ...settings!.confessions!,
                                                    reactions: {
                                                        ...settings!.confessions!.reactions!,
                                                        upvote: e.target.value
                                                    }
                                                }
                                            })}
                                            className="w-full bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                                            placeholder="👍"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm text-white/60">Downvote Reaction</label>
                                        <input 
                                            type="text"
                                            value={settings.confessions.reactions.downvote}
                                            onChange={(e) => updateSettings({
                                                confessions: {
                                                    ...settings!.confessions!,
                                                    reactions: {
                                                        ...settings!.confessions!.reactions,
                                                        downvote: e.target.value
                                                    }
                                                }
                                            })}
                                            className="w-full bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                                            placeholder="👎"
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <label className="text-sm text-white/60">Blacklisted Words</label>
                                        <button
                                            onClick={() => setShowBlacklistDialog(true)}
                                            className="text-sm text-white/60 hover:text-white"
                                        >
                                            <Plus className="w-4 h-4" />
                                        </button>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        {settings.confessions.blacklisted_words.map((word) => (
                                            <div 
                                                key={word}
                                                className="flex items-center gap-2 px-2 py-1 bg-white/[0.02] rounded-lg"
                                            >
                                                <span className="text-sm">{word}</span>
                                                <button
                                                    onClick={() => updateSettings({
                                                        confessions: {
                                                            ...settings!.confessions!,
                                                            blacklisted_words: settings!.confessions!.blacklisted_words.filter(w => w !== word)
                                                        }
                                                    })}
                                                    className="p-1 hover:bg-white/5 rounded"
                                                >
                                                    <X className="w-3 h-3 text-white/60" />
                                                </button>
                                            </div>
                                        ))}
                                        {settings.confessions.blacklisted_words.length === 0 && (
                                            <div className="text-sm text-white/60">No blacklisted words</div>
                                        )}
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <label className="text-sm text-white/60">Muted Users</label>
                                        <button
                                            onClick={() => setShowMuteDialog(true)}
                                            className="text-sm text-white/60 hover:text-white"
                                        >
                                            <Plus className="w-4 h-4" />
                                        </button>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        {settings.confessions.muted_users.map((userId) => (
                                            <div 
                                                key={userId}
                                                className="flex items-center gap-2 px-2 py-1 bg-white/[0.02] rounded-lg"
                                            >
                                                <span className="text-sm">{userId}</span>
                                                <button
                                                    onClick={() => updateSettings({
                                                        confessions: {
                                                            ...settings!.confessions!,
                                                            muted_users: settings!.confessions!.muted_users.filter(id => id !== userId)
                                                        }
                                                    })}
                                                    className="p-1 hover:bg-white/5 rounded"
                                                >
                                                    <X className="w-3 h-3 text-white/60" />
                                                </button>
                                            </div>
                                        ))}
                                        {settings.confessions.muted_users.length === 0 && (
                                            <div className="text-sm text-white/60">No muted users</div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {settings?.join_dm && (
                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                        <UserPlus className="w-5 h-5 text-white/60" />
                        <h2 className="text-base font-medium text-white">Join Message</h2>
                    </div>
                    <div className="space-y-6">
                        <ProtectionSettings
                            title="Enable Join DM"
                            description="Send a welcome message when users join"
                            enabled={settings!.join_dm!.enabled}
                            onToggle={(enabled) => updateSettings({
                                join_dm: {
                                    ...settings!.join_dm!,
                                    enabled
                                }
                            })}
                        />
                        {settings.join_dm.enabled && (
                            <div className="space-y-4 pl-6 border-l border-white/10">
                                <div className="space-y-2">
                                    <label className="text-sm text-white/60">Welcome Message</label>
                                    <div className="relative">
                                        <textarea 
                                            value={settings.join_dm.message}
                                            onChange={(e) => updateSettings({
                                                join_dm: {
                                                    ...settings!.join_dm!,
                                                    message: e.target.value
                                                }
                                            })}
                                            placeholder="Welcome message template"
                                            className="w-full h-24 bg-[#0B0C0C] border border-white/10 rounded-lg px-3 py-2 text-white resize-none"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => openBuilder(settings!.join_dm!.message, (newValue) => {
                                                updateSettings({
                                                    join_dm: {
                                                        ...settings!.join_dm!,
                                                        message: newValue
                                                    }
                                                })
                                            })}
                                            className="absolute top-2 right-2 p-1 hover:bg-white/5 rounded transition-colors"
                                        >
                                            <Code className="w-4 h-4 text-white/60" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {settings?.restricted_commands && (
                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <ShieldAlert className="w-5 h-5 text-white/60" />
                            <h2 className="text-base font-medium text-white">Restricted Commands</h2>
                        </div>
                        <button
                            onClick={() => setShowCommandDialog(true)}
                            className="px-4 py-2 text-sm bg-evict-500 text-white rounded-lg hover:bg-evict-600 transition-colors"
                        >
                            Add Command
                        </button>
                    </div>
                    <div className="space-y-4">
                        {Object.entries(settings.restricted_commands).length === 0 ? (
                            <div className="text-center py-8 text-white/60">
                                No command restrictions added
                            </div>
                        ) : (
                            Object.entries(settings.restricted_commands).map(([command, roleId]) => (
                                <div key={command} className="flex items-center gap-4 p-3 bg-white/[0.02] rounded-lg">
                                    <div className="flex-1">
                                        <div className="text-sm text-white/60 mb-1">/{command}</div>
                                        <Dropdown
                                            value={roleId ?? ""}
                                            onChange={(value) => updateSettings({
                                                restricted_commands: {
                                                    ...settings.restricted_commands,
                                                    [command]: value
                                                }
                                            })}
                                            placeholder="Select a role"
                                            options={roleOptions}
                                        />
                                    </div>
                                    <button
                                        onClick={() => {
                                            const newCommands = { ...settings.restricted_commands }
                                            delete newCommands[command]
                                            updateSettings({ restricted_commands: newCommands })
                                        }}
                                        className="p-2 hover:bg-white/5 rounded transition-colors"
                                    >
                                        <X className="w-4 h-4 text-white/60" />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>

                    <CommandDialog 
                        open={showCommandDialog} 
                        onClose={() => setShowCommandDialog(false)}
                        roleOptions={roleOptions}
                        onAdd={(command, roleId) => {
                            if (settings?.restricted_commands) {
                                updateSettings({
                                    restricted_commands: {
                                        ...settings.restricted_commands,
                                        [command]: roleId
                                    }
                                })
                            }
                        }}
                    />
                </div>
            )}

            <SaveButton 
                hasChanges={hasChanges}
                isSaving={isSaving}
                onSave={handleSave}
            />

            <EmbedBuilder />

            <BlacklistDialog 
                open={showBlacklistDialog}
                onClose={() => setShowBlacklistDialog(false)}
                onAdd={(word) => {
                    if (!settings?.confessions!.blacklisted_words.includes(word)) {
                        updateSettings({
                            confessions: {
                                ...settings!.confessions!,
                                blacklisted_words: [...settings!.confessions!.blacklisted_words, word]
                            }
                        })
                    }
                }}
            />

            <MuteUserDialog 
                open={showMuteDialog}
                onClose={() => setShowMuteDialog(false)}
                onAdd={(userId) => {
                    if (!settings?.confessions?.muted_users.includes(userId)) {
                        updateSettings({
                            confessions: {
                                ...settings!.confessions!,
                                muted_users: [...settings!.confessions!.muted_users, userId]
                            }
                        })
                    }
                }}
            />
        </div>
    )
} 