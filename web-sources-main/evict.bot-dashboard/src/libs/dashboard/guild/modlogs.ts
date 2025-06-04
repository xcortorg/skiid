export interface UserData {
    user_id: string;
    user_name: string;
    user_displayname: string;
    user_avatar: string;
}

export interface ModCase {
    id: number;
    user_id: number;
    moderator_id: number;
    timestamp: string;
    reason: string;
    action: string;
    duration: string | null;
    guild_id: number;
    case_id: number;
    role_id: string | null;
}

export interface ModConfig {
    guild_id: number;
    channel_id: string | null;
    jail_id: string | null;
    role_id: string | null;
    dm_enabled: boolean;
    dm_ban: string | null;
    dm_kick: string | null;
    dm_mute: string | null;
    dm_unban: string | null;
    dm_jail: string | null;
    dm_unjail: string | null;
    dm_unmute: string | null;
    dm_warn: string | null;
    dm_timeout: string | null;
    dm_untimeout: string | null;
    roles: string;
    user_id: number;
    dm_antinuke_ban: string | null;
    dm_antinuke_kick: string | null;
    dm_antinuke_strip: string | null;
    dm_antiraid_ban: string | null;
    dm_antiraid_kick: string | null;
    dm_antiraid_timeout: string | null;
    dm_antiraid_strip: string | null;
    dm_role_add: string | null;
    dm_role_remove: string | null;
}

export interface ModLogsResponse {
    guild_id: string;
    enabled: boolean;
    config: ModConfig | null;
    users: UserData[];
    cases: ModCase[];
    // permissions: {
    //     owner: boolean;
    // };
}

export interface ErrorResponse {
    error: string;
}

export async function fetchGuildModLogs(guildId: string): Promise<ModLogsResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/modlogs`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-GUILD-ID': guildId,
        }
    })

    if (!response.ok) {
        const error = await response.json() as ErrorResponse
        throw new Error(error.error || 'Failed to fetch mod logs')
    }

    const data = await response.json()
    return data
}
