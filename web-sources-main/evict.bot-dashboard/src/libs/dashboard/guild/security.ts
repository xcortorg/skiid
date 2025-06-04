export interface SecuritySettings {
    guild_id: string;
    permissions: {
        manage_guild: boolean;
        trusted_antinuke: boolean;
        owner: boolean;
    };
    antiraid: {
        guild_id: string;
        locked: boolean;
        joins: any;
        mentions: any;
        avatar: any;
        browser: any;
    } | null;
    antinuke: {
        guild_id: string;
        whitelist: string[];
        trusted_admins: string[];
        bot: boolean;
        ban: any;
        kick: any;
        role: any;
        channel: any;
        webhook: any;
        emoji: any;
    } | null;
}

export interface SecurityUpdateRequest {
    antiraid?: {
        guild_id: string
        locked: boolean
        joins: any
        mentions: any
        avatar: any
        browser: any
    }
    antinuke?: {
        guild_id: string
        whitelist: string[]
        trusted_admins: string[]
        bot: boolean
        ban: any
        kick: any
        role: any
        channel: any
        webhook: any
        emoji: any
    }
}

export interface SecurityUpdateResponse {
    guild_id: string
    permissions: {
        manage_guild: boolean
        trusted_antinuke: boolean
        owner: boolean
    }
    antiraid: {
        guild_id: string
        locked: boolean
        joins: any
        mentions: any
        avatar: any
        browser: any
    } | null
    antinuke: {
        guild_id: string
        whitelist: string[]
        trusted_admins: string[]
        bot: boolean
        ban: any
        kick: any
        role: any
        channel: any
        webhook: any
        emoji: any
    } | null
}

export interface ErrorResponse {
    error: string
}

export async function fetchGuildSecurity(guildId: string): Promise<SecuritySettings> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/security`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-GUILD-ID': guildId
        }
    })

    if (!response.ok) {
        const error = await response.json() as ErrorResponse
        throw new Error(error.error || 'Failed to fetch security settings')
    }

    const data = await response.json()
    
    if (data.antinuke) {
        data.antinuke.trusted_admins = data.antinuke.trusted_admins.map((id: any) => `${id}`)
        data.antinuke.whitelist = data.antinuke.whitelist.map((id: any) => `${id}`)
    }
    
    return data
}

export async function updateGuildSecurity(guildId: string, settings: SecurityUpdateRequest): Promise<SecuritySettings> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }
    
    const response = await fetch(`https://api.evict.bot/update/security`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-GUILD-ID': guildId,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })

    if (!response.ok) {
        const error = await response.json() as ErrorResponse
        throw new Error(error.error || 'Failed to update security settings')
    }

    const data = await response.json()
    if (data.antinuke) {
        data.antinuke.trusted_admins = data.antinuke.trusted_admins.map((id: any) => `${id}`)
        data.antinuke.whitelist = data.antinuke.whitelist.map((id: any) => `${id}`)
    }
    return data
}