export interface AutomationResponse {
    guild_id: string
    permissions: {
        manage_messages: boolean
        administrator: boolean
    }
    users: Array<{
        id: string
        name: string
        display_name: string
        avatar: string
    }>
    tags: {
        count: number
        items: Array<{
            name: string
            content: string
            owner_id: string
            uses: number
            created_at: string
            aliases: string[]
        }>
    }
    trackers: {
        vanity: {
            channel: {
                id: string
                name: string
                type: string
            }
        }
        usernames: {
            channel: {
                id: string
                name: string
                type: string
            }
        }
    }
    autoresponses: {
        count: number
        items: Array<{
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
        }>
    }
    reactions: {
        count: number
        items: Array<{
            trigger: string
            reactions: string[]
        }>
        limits: {
            max_per_trigger: number
            trigger_length: number
        }
    }
    profiles: {
        count: number
        items: Array<{
            channel: {
                id: string
                name: string
                type: string
            }
            type: "banner" | "pfp"
            category: string
        }>
        types: {
            pfp: {
                categories: string[]
            }
            banner: {
                categories: string[]
                case_map: { [key: string]: string }
            }
        }
    }
}

export async function fetchGuildAutomation(guildId: string): Promise<AutomationResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/automation`, {
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
        throw new Error("Failed to fetch automation")
    }

    return response.json()
}

export interface AutomationUpdate {
    tags?: Array<{
        type: "create" | "edit" | "delete"
        name: string
        content?: string
    }>
    autoresponses?: Array<{
        type: "create" | "edit" | "delete"
        original_trigger: string
        trigger: string
        content?: string
        settings?: {
            strict: boolean
            reply: boolean
            delete: boolean
            delete_after: number
            role?: {
                id: string
            }
        }
    }>
    reactions?: Array<{
        type: "create" | "delete"
        trigger: string
        emojis?: string[]
    }>
    profiles?: Array<{
        type: "create" | "delete"
        channel: {
            id: string
        }
        media_type: "pfp" | "banner"
        category?: string
    }>
    trackers?: {
        vanity?: {
            channel: {
                id: string
            }
        } | null
        usernames?: {
            channel: {
                id: string
            }
        } | null
    }
}

export async function updateGuildAutomation(guildId: string, data: AutomationUpdate): Promise<void> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/update/automation`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            "X-GUILD-ID": guildId
        },
        body: JSON.stringify(data)
    })

    if (response.status === 401) {
        throw new Error("Unauthorized")
    }

    if (response.status === 403) {
        throw new Error("Missing required permissions or bot not in server")
    }

    if (!response.ok) {
        throw new Error("Failed to update automation")
    }
}