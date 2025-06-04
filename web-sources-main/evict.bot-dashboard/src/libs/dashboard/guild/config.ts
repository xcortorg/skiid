export interface ConfigResponse {
    guild_id: string
    prefix: string
    moderation: {
        enabled: boolean
        dm_notifications: {
            enabled: boolean
            actions: { [key: string]: boolean }
            messages: { [key: string]: string }
            invoke_messages: {
                [key: string]: {
                    enabled: boolean
                    message: string
                }
            }
        }
        whitelist: {
            enabled: boolean
            action: "kick" | "ban"
        }
        vanity: {
            enabled: boolean
            role_id: string | null
            channel_id: string | null
            template: string | null
            default_template: string
        }
        ping_on_join: {
            enabled: boolean
            channels: string[]
        } | null
    }
    confessions?: {
        enabled: boolean
        channel_id: string | null
        total_confessions: number
        reactions: {
            upvote: string
            downvote: string
        }
        blacklisted_words: string[]
        muted_users: string[]
    }
    join_dm?: {
        enabled: boolean
        message: string
    }
    restricted_commands?: Record<string, string | null>
}

export interface ConfigRequest {
    prefix?: string
    moderation?: {
        dm_notifications?: {
            enabled: boolean
            actions?: { [key: string]: boolean }
            messages?: { [key: string]: string }
            invoke_messages?: {
                [key: string]: {
                    enabled: boolean
                    message: string
                }
            }
        }
    }
    whitelist?: {
        enabled: boolean
        action: "kick" | "ban"
    }
    vanity?: {
        enabled: boolean
        role_id?: string | null
        channel_id?: string | null
        template?: string | null
    }
    confessions?: {
        enabled: boolean
        channel_id: string | null
        reactions: {
            upvote: string
            downvote: string
        }
        blacklisted_words: string[]
        muted_users: string[]
    }
    join_dm?: {
        enabled: boolean
        message: string
    }
    restricted_commands?: Record<string, string | null>
}

interface SecurityRequest {
    antiraid?: {
        status: boolean;
        punishment: "timeout" | "ban" | "kick";
        whitelist: boolean;
        joins: number;
        seconds: number;
    };
    antinuke?: {
        status: boolean;
        punishment: "ban";
        whitelist: boolean;
        trusted_admins: string[];
    };
}

export interface SecuritySettings {
    antiraid: {
        enabled: boolean;
        status: boolean;
        punishment: "timeout" | "ban" | "kick";
        whitelist: boolean;
        joins: number;
        seconds: number;
    };
    antinuke: {
        enabled: boolean;
        status: boolean;
        punishment: "ban";
        whitelist: boolean;
        trusted_admins: string[];
    };
}

export async function fetchGuildConfig(guildId: string): Promise<ConfigResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/config`, {
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
        throw new Error("Missing required permissions or bot not in server")
    }

    if (!response.ok) {
        throw new Error("Failed to fetch config")
    }

    return response.json()
}

export async function updateGuildConfig(
    guildId: string,
    settings: ConfigRequest
): Promise<ConfigResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/update/config`, {
        method: "POST",
        headers: {
            Authorization: `Bearer ${token}`,
            "X-GUILD-ID": guildId,
            "Content-Type": "application/json",
            Origin: "https://evict.bot"
        },
        body: JSON.stringify(settings)
    })

    if (response.status === 401) {
        throw new Error("Session expired")
    }

    if (response.status === 403) {
        throw new Error("Missing required permissions or bot not in server")
    }

    if (!response.ok) {
        throw new Error("Failed to update config")
    }

    return response.json()
}
