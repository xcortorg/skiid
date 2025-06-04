import { checkBetaAccess } from './beta'

interface GuildPermissions {
    admin: boolean;
    manage_guild: boolean;
    manage_roles: boolean;
    manage_channels: boolean;
    kick_members: boolean;
    ban_members: boolean;
    value: number;
}

export interface DiscordGuild {
    id: string;
    name: string;
    icon: string | null;
    owner: boolean;
    permissions: GuildPermissions;
    features: string[];
    mutual: boolean;
}


interface DiscordUser {
    id: string;
    username: string;
    discriminator: string;
    avatar: string | null;
}

export interface DashboardResponse {
    success: boolean;
    user: DiscordUser;
    guilds: DiscordGuild[];
    notifications: {
        id: string;
        user_id: string | null;
        title: string;
        content: string;
        type: "info" | "warning" | "error" | "success";
        created_at: string;
        expires_at: string | null;
    }[];
}

export function canManageGuild(guild: DiscordGuild): boolean {
    return (guild.permissions.manage_guild || guild.permissions.admin || guild.owner) && guild.mutual
}

export async function fetchUserGuilds(): Promise<DashboardResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const betaAccess = await checkBetaAccess()
    if (!betaAccess.has_access) {
        throw new Error("Beta access required")
    }

    const response = await fetch("https://api.evict.bot/dashboard/guilds", {
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
        }
    })

    if (response.status === 401) {
        throw new Error("Unauthorized")
    }

    if (!response.ok) {
        throw new Error("Failed to fetch guilds")
    }

    return response.json()
}

export interface RolesResponse {
    roles: {
        id: string;
        name: string;
        color: number;
        position: number;
        permissions: number;
        mentionable: boolean;
        hoist: boolean;
        managed: boolean;
        icon: string | null;
    }[];
}

export interface ChannelsResponse {
    categories: {
        id: string;
        name: string;
        position: number;
        nsfw: boolean;
    }[];
    channels: {
        id: string;
        name: string;
        position: number;
        type: string;
        category_id: string | null;
        nsfw: boolean;
        topic?: string;
        slowmode_delay?: number;
        news?: boolean;
        bitrate?: number;
        user_limit?: number;
        rtc_region?: string | null;
        default_auto_archive_duration?: number;
    }[];
}

const cache = new Map<string, { data: any; timestamp: number }>();
const CACHE_DURATION = 1000 * 60 * 5;

async function fetchWithCache<T>(
    key: string,
    fetcher: () => Promise<T>
): Promise<T> {
    const cached = cache.get(key);
    const now = Date.now();

    if (cached && now - cached.timestamp < CACHE_DURATION) {
        return cached.data as T;
    }

    const data = await fetcher();
    cache.set(key, { data, timestamp: now });
    return data;
}

export async function fetchGuildRoles(guildId: string): Promise<RolesResponse> {
    return fetchWithCache(`roles-${guildId}`, async () => {
        const token = localStorage.getItem('userToken')
        if (!token) {
            throw new Error("Unauthorized")
        }

        const betaAccess = await checkBetaAccess()
        if (!betaAccess.has_access) {
            throw new Error("Beta access required")
        }

        const response = await fetch(`https://api.evict.bot/roles`, {
            headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
                "X-GUILD-ID": guildId
            }
        })

        if (response.status === 401) {
            throw new Error("Unauthorized")
        }

        if (response.status === 403) {
            throw new Error("Missing required permissions")
        }

        if (!response.ok) {
            throw new Error("Failed to fetch roles")
        }

        return response.json()
    })
}

export async function fetchGuildChannels(guildId: string): Promise<ChannelsResponse> {
    return fetchWithCache(`channels-${guildId}`, async () => {
        const token = localStorage.getItem('userToken')
        if (!token) {
            throw new Error("Unauthorized")
        }

        const betaAccess = await checkBetaAccess()
        if (!betaAccess.has_access) {
            throw new Error("Beta access required")
        }

        const response = await fetch(`https://api.evict.bot/channels`, {
            headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
                "X-GUILD-ID": guildId
            }
        })

        if (response.status === 401) {
            throw new Error("Unauthorized")
        }

        if (response.status === 403) {
            throw new Error("Missing required permissions")
        }

        if (!response.ok) {
            throw new Error("Failed to fetch channels")
        }

        return response.json()
    })
}

export interface GuildSettings {
    meta: {
        cached: boolean
    }
    guild: {
        id: string
        name: string
        icon: string
        member_count: number
        owner_id: string
        created_at: string
        features: string[]
    }
    settings: {
        enabled: boolean | null
        prefixes: string[]
        level: number | null
        reskin: boolean
        reposter: {
            prefix: boolean
            delete: boolean
            embed: boolean
            methods: string[]
        }
        verification: {
            channel_id: string | null
            role_id: string | null
            timeout: number | null
            ip_limit: number | null
            vpn_check: boolean | null
            private_tab_check: boolean | null
        }
        boosters: {
            role_base_id: string
            role_include_ids: string[]
        }
        logging: {
            channel_id: string | null
            ignore_ids: string[]
        }
        locking: {
            role_id: string | null
            ignore_ids: string[]
        }
        reassign: {
            enabled: boolean
            ignore_ids: string[]
        }
        invoke_commands: {
            kick: string | null
            ban: string | null
            unban: string | null
            timeout: string | null
            untimeout: string | null
            play: string | null
        }
        play: {
            panel: boolean
            deletion: boolean
        }
        transcription: boolean
        welcome_removal: boolean
        safesearch_level: string
        author: string | null
    }
    recent_commands: {
        command: string
        category: string
        user_id: string
        timestamp: string
    }[]
}

export async function fetchGuildSettings(guildId: string): Promise<GuildSettings> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("403")
    }

    const response = await fetch(`https://api.evict.bot/guild-settings?guild_id=${guildId}`, {
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
        }
    })

    if (!response.ok) {
        if (response.status === 403) {
            throw new Error("403")
        }
        throw new Error("Failed to fetch guild settings")
    }

    return response.json()
}