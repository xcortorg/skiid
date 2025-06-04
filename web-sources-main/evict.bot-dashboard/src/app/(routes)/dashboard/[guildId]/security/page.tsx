"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { fetchGuildSecurity, SecuritySettings, updateGuildSecurity, SecurityUpdateRequest } from "@/libs/dashboard/guild/security"
import { useState, useEffect } from "react"
import WhitelistManager from "../components/security/WhitelistManager"
import SaveButton from "../components/security/SaveButton"
import { Shield, Users, Beaker } from "lucide-react"
import { toast } from "react-hot-toast"
import { checkBetaAccess } from "@/libs/dashboard/beta"
import { useRouter } from "next/navigation"

interface ProtectionConfig {
    threshold: number;
    duration: number;
    punishment: 'ban' | 'kick';
}

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

function Switch({ checked, onCheckedChange }: { checked: boolean, onCheckedChange: (checked: boolean) => void }) {
    return (
        <button
            onClick={() => onCheckedChange(!checked)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                checked ? 'bg-blue-600' : 'bg-white/10'
            }`}
        >
            <span
                className={`${
                    checked ? 'translate-x-6' : 'translate-x-1'
                } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
            />
        </button>
    )
}

export default function SecurityPage({ params }: { params: { guildId: string } }) {
    const queryClient = useQueryClient()
    const [hasChanges, setHasChanges] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [settings, setSettings] = useState<SecuritySettings | null>(null)
    const router = useRouter()

    const { data: betaAccess } = useQuery({
        queryKey: ["beta"],
        queryFn: checkBetaAccess,
        staleTime: 1000 * 60 * 15
    })

    const { data: securityData } = useQuery({
        queryKey: ["security", params.guildId],
        queryFn: () => fetchGuildSecurity(params.guildId),
        enabled: !!betaAccess?.has_access,
        staleTime: 1000 * 60 * 5,
        placeholderData: (prev) => prev
    })

    useEffect(() => {
        if (!settings && securityData) {
            const initialSettings = {
                ...securityData,
                antiraid: securityData.antiraid || {
                    guild_id: params.guildId,
                    locked: false,
                    joins: null,
                    mentions: null,
                    avatar: null,
                    browser: null
                }
            }
            setSettings(initialSettings)
        }
    }, [securityData, settings, params.guildId])

    const updateSettings = (newSettings: Partial<SecuritySettings>) => {
        setSettings(prev => {
            if (!prev) return null
            setHasChanges(true)
            return { ...prev, ...newSettings }
        })
    }

    const handleSave = async () => {
        if (!settings?.antiraid || !settings?.antinuke) {
            console.log("Missing settings:", { antiraid: settings?.antiraid, antinuke: settings?.antinuke })
            return
        }

        setIsSaving(true)
        try {
            const payload: SecurityUpdateRequest = {
                antiraid: {
                    guild_id: params.guildId,
                    locked: settings.antiraid.locked,
                    joins: settings.antiraid.joins,
                    mentions: settings.antiraid.mentions,
                    avatar: settings.antiraid.avatar,
                    browser: settings.antiraid.browser
                },
                antinuke: {
                    guild_id: params.guildId,
                    whitelist: settings.antinuke.whitelist.map(String),
                    trusted_admins: settings.antinuke.trusted_admins.map(String),
                    bot: settings.antinuke.bot,
                    ban: settings.antinuke.ban !== null,
                    kick: settings.antinuke.kick !== null,
                    role: settings.antinuke.role !== null,
                    channel: settings.antinuke.channel !== null,
                    webhook: settings.antinuke.webhook !== null,
                    emoji: settings.antinuke.emoji !== null
                }
            }

            await updateGuildSecurity(params.guildId, payload)
            
            queryClient.setQueryData(["security", params.guildId], settings)
            
            setHasChanges(false)
            toast.success('Settings saved successfully')
        } catch (error: any) {
            console.error('Save error:', error)
            if (error?.response?.data?.error === "Only the server owner can modify the antinuke whitelist") {
                toast.error("Only the server owner can modify the antinuke whitelist")
            } else {
                toast.error('Failed to save settings')
            }
        } finally {
            setIsSaving(false)
        }
    }

    const handleProtectionToggle = (
        type: 'ban' | 'kick' | 'role' | 'channel' | 'webhook' | 'emoji',
        enabled: boolean
    ) => {
        updateSettings({
            antinuke: {
                ...settings!.antinuke!,
                [type]: enabled ? {
                    threshold: 5,
                    duration: 60,
                    punishment: 'ban'
                } : null,
                guild_id: settings!.antinuke!.guild_id
            }
        })
    }

    const handleProtectionConfigChange = (
        type: 'ban' | 'kick',
        config: Partial<ProtectionConfig>
    ) => {
        updateSettings({
            antinuke: {
                ...settings!.antinuke!,
                [type]: {
                    ...settings!.antinuke![type],
                    ...config
                },
                guild_id: settings!.antinuke!.guild_id
            }
        })
    }

    if (betaAccess && !betaAccess.has_access) {
        return <BetaAccessRequired />
    }

    if (securityData === undefined) {
        return (
            <div className="space-y-6">
                <div className="animate-pulse space-y-2">
                    <div className="bg-white/5 h-8 w-32 rounded" />
                    <div className="bg-white/5 h-5 w-64 rounded" />
                </div>

                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                    <div className="animate-pulse space-y-4">
                        <div className="bg-white/5 h-6 w-32 rounded" />
                        <div className="flex gap-3">
                            {[...Array(3)].map((_, i) => (
                                <div key={i} className="bg-white/5 h-8 w-24 rounded-lg" />
                            ))}
                        </div>
                    </div>
                </div>

                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                    <div className="animate-pulse space-y-4">
                        <div className="bg-white/5 h-6 w-40 rounded" />
                        <div className="space-y-3">
                            {[...Array(4)].map((_, i) => (
                                <div key={i} className="bg-white/5 h-12 rounded-lg" />
                            ))}
                        </div>
                    </div>
                </div>

                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                    <div className="animate-pulse space-y-4">
                        <div className="bg-white/5 h-6 w-40 rounded" />
                        <div className="space-y-3">
                            {[...Array(6)].map((_, i) => (
                                <div key={i} className="bg-white/5 h-12 rounded-lg" />
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-xl md:text-2xl font-bold text-white">Security</h1>
                <p className="text-white/60">Configure your server&apos;s security settings</p>
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <h2 className="text-base font-medium text-white mb-4">Permissions</h2>
                <div className="flex gap-3">
                    <div className={`px-3 py-1.5 rounded-lg text-sm ${
                        securityData?.permissions.manage_guild 
                            ? 'bg-green-500/10 text-green-500' 
                            : 'bg-red-500/10 text-red-500'
                    }`}>
                        Manage Server
                    </div>
                    <div className={`px-3 py-1.5 rounded-lg text-sm ${
                        securityData?.permissions.trusted_antinuke 
                            ? 'bg-green-500/10 text-green-500' 
                            : 'bg-red-500/10 text-red-500'
                    }`}>
                        Trusted Anti-Nuke
                    </div>
                    <div className={`px-3 py-1.5 rounded-lg text-sm ${
                        securityData?.permissions.owner 
                            ? 'bg-green-500/10 text-green-500' 
                            : 'bg-red-500/10 text-red-500'
                    }`}>
                        Server Owner
                    </div>
                </div>
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Users className="w-5 h-5 text-white/60" />
                    <h2 className="text-base font-medium text-white">Anti-Raid Protection</h2>
                </div>
                {settings?.antiraid && (
                    <div className="space-y-4">
                        <ProtectionSettings
                            title="Server Lockdown"
                            description="Automatically lock the server during raid attempts"
                            enabled={settings.antiraid.locked}
                            onToggle={(enabled) => updateSettings({
                                antiraid: { 
                                    ...settings.antiraid!,
                                    locked: enabled,
                                    guild_id: settings.antiraid!.guild_id
                                }
                            })}
                        />
                        <ProtectionSettings
                            title="Join Rate Limits"
                            description="Prevent mass joins in short time periods"
                            enabled={!!settings.antiraid.joins}
                            onToggle={(enabled) => updateSettings({
                                antiraid: { 
                                    ...settings.antiraid!,
                                    joins: enabled ? {} : null,
                                    guild_id: settings.antiraid!.guild_id
                                }
                            })}
                        />
                        <ProtectionSettings
                            title="Mention Spam Protection"
                            description="Prevent mass mentions and spam"
                            enabled={!!settings.antiraid.mentions}
                            onToggle={(enabled) => updateSettings({
                                antiraid: { 
                                    ...settings.antiraid!,
                                    mentions: enabled ? {} : null,
                                    guild_id: settings.antiraid!.guild_id
                                }
                            })}
                        />
                        <ProtectionSettings
                            title="Avatar Detection"
                            description="Detect and act on suspicious profile pictures"
                            enabled={!!settings.antiraid.avatar}
                            onToggle={(enabled) => updateSettings({
                                antiraid: { 
                                    ...settings.antiraid!,
                                    avatar: enabled ? {} : null,
                                    guild_id: settings.antiraid!.guild_id
                                }
                            })}
                        />
                    </div>
                )}
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Shield className="w-5 h-5 text-white/60" />
                    <h2 className="text-base font-medium text-white">Anti-Nuke Protection</h2>
                </div>
                {settings?.antinuke && (
                    <div className="space-y-6">
                        <ProtectionSettings
                            title="Bot Protection"
                            description="Prevent unauthorized bot actions"
                            enabled={settings.antinuke.bot}
                            onToggle={(enabled) => updateSettings({
                                antinuke: { 
                                    ...settings.antinuke!,
                                    bot: enabled,
                                    guild_id: settings.antinuke!.guild_id
                                }
                            })}
                        />

                        <WhitelistManager 
                            isOwner={settings.permissions.owner}
                            whitelist={settings.antinuke.whitelist}
                            trustedAdmins={settings.antinuke.trusted_admins}
                            onWhitelistChange={(whitelist) => updateSettings({
                                antinuke: { 
                                    ...settings.antinuke!,
                                    whitelist,
                                    guild_id: settings.antinuke!.guild_id
                                }
                            })}
                            onTrustedAdminsChange={(trusted_admins) => updateSettings({
                                antinuke: { 
                                    ...settings.antinuke!,
                                    trusted_admins,
                                    guild_id: settings.antinuke!.guild_id
                                }
                            })}
                        />

                        <div className="space-y-4">
                            <h3 className="text-sm font-medium text-white">Protection Settings</h3>
                            <div className="space-y-4">
                                <ProtectionSettings
                                    title="Ban Protection"
                                    description="Prevent mass bans"
                                    enabled={!!settings.antinuke.ban}
                                    onToggle={(enabled) => handleProtectionToggle('ban', enabled)}
                                    config={settings.antinuke.ban as ProtectionConfig}
                                    onConfigChange={(config) => handleProtectionConfigChange('ban', config)}
                                    showConfig={true}
                                />
                                <ProtectionSettings
                                    title="Kick Protection"
                                    description="Prevent mass kicks"
                                    enabled={!!settings.antinuke.kick}
                                    onToggle={(enabled) => handleProtectionToggle('kick', enabled)}
                                    config={settings.antinuke.kick as ProtectionConfig}
                                    onConfigChange={(config) => handleProtectionConfigChange('kick', config)}
                                    showConfig={true}
                                />
                                <ProtectionSettings
                                    title="Role Protection"
                                    description="Prevent role modifications"
                                    enabled={!!settings.antinuke.role}
                                    onToggle={(enabled) => handleProtectionToggle('role', enabled)}
                                    showConfig={false}
                                />
                                <ProtectionSettings
                                    title="Channel Protection"
                                    description="Prevent channel deletion and modification"
                                    enabled={!!settings.antinuke.channel}
                                    onToggle={(enabled) => handleProtectionToggle('channel', enabled)}
                                    showConfig={false}
                                />
                                <ProtectionSettings
                                    title="Webhook Protection"
                                    description="Prevent unauthorized webhook creation"
                                    enabled={!!settings.antinuke.webhook}
                                    onToggle={(enabled) => handleProtectionToggle('webhook', enabled)}
                                    showConfig={false}
                                />
                                <ProtectionSettings
                                    title="Emoji Protection"
                                    description="Prevent emoji deletion and modification"
                                    enabled={!!settings.antinuke.emoji}
                                    onToggle={(enabled) => handleProtectionToggle('emoji', enabled)}
                                    showConfig={false}
                                />
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <SaveButton 
                hasChanges={hasChanges}
                isSaving={isSaving}
                onSave={handleSave}
            />
        </div>
    )
}

interface ProtectionSettingsProps {
    title: string;
    description: string;
    enabled: boolean;
    onToggle: (enabled: boolean) => void;
    config?: ProtectionConfig;
    onConfigChange?: (config: Partial<ProtectionConfig>) => void;
    showConfig?: boolean;
}

function ProtectionSettings({
    title,
    description,
    enabled,
    onToggle,
    config,
    onConfigChange
}: ProtectionSettingsProps) {
    return (
        <div className="bg-[#141414] rounded-lg">
            <div className="flex items-center justify-between p-4">
                <div>
                    <h3 className="text-white font-medium">{title}</h3>
                    <p className="text-[#888] text-sm">{description}</p>
                </div>
                <Switch checked={enabled} onCheckedChange={onToggle} />
            </div>
            
            {enabled && (
                <div className="bg-black/20 p-4 space-y-3 border-t border-white/5">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-sm text-[#888] block mb-2">Threshold</label>
                            <input
                                type="number"
                                value={config?.threshold ?? 5}
                                onChange={(e) => onConfigChange?.({ threshold: parseInt(e.target.value) })}
                                className="w-full bg-black/40 rounded px-3 py-2 text-white border border-white/5"
                                min={1}
                                max={10}
                                required
                            />
                        </div>
                        <div>
                            <label className="text-sm text-[#888] block mb-2">Duration (seconds)</label>
                            <input
                                type="number"
                                value={config?.duration ?? 60}
                                onChange={(e) => onConfigChange?.({ duration: parseInt(e.target.value) })}
                                className="w-full bg-black/40 rounded px-3 py-2 text-white border border-white/5"
                                min={30}
                                max={300}
                                required
                            />
                        </div>
                    </div>
                    <div>
                        <label className="text-sm text-[#888] block mb-2">Punishment</label>
                        <select
                            value={config?.punishment ?? 'ban'}
                            onChange={(e) => onConfigChange?.({ punishment: e.target.value as 'ban' | 'kick' })}
                            className="w-full bg-black/40 rounded px-3 py-2 text-white border border-white/5"
                            required
                        >
                            <option value="ban">Ban</option>
                            <option value="kick">Kick</option>
                        </select>
                    </div>
                </div>
            )}
        </div>
    )
} 