export interface GreetingsResponse {
    guild_id: string
    permissions: {
        manage_guild: boolean
        administrator: boolean
    }
    welcome: {
        count: number
        items: Array<any> 
        limits: {
            max_messages: number
        }
        removal: boolean
    }
    goodbye: {
        count: number
        items: Array<any>
        limits: {
            max_messages: number
        }
    }
}

export async function fetchGuildGreetings(guildId: string): Promise<GreetingsResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/greetings`, {
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
        throw new Error("Failed to fetch greetings")
    }

    return response.json()
}

export interface GreetingsUpdate {
    welcome?: Array<{
        type: "create" | "edit" | "delete"
        channel: {
            id: string
        }
        content?: string
        delete_after?: number
    }>
    goodbye?: Array<{
        type: "create" | "edit" | "delete"
        channel: {
            id: string
        }
        content?: string
        delete_after?: number
    }>
    settings?: {
        welcome_removal?: boolean
    }
}

export async function updateGuildGreetings(guildId: string, data: GreetingsUpdate): Promise<void> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/update/greetings`, {
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
        throw new Error("Failed to update greetings")
    }
} 