interface InvokeUser {
    user_id: string
    user_name: string
    user_displayname: string
    user_avatar: string
}

interface InvokeRecord {
    user_id: string
    command: string
    category: string
    timestamp: string
}

export interface InvokesResponse {
    guild_id: string
    total_invokes: number
    users: InvokeUser[]
    invokes: InvokeRecord[]
}

export async function fetchGuildInvokes(guildId: string): Promise<InvokesResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/invokes`, {
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
        throw new Error("Failed to fetch invokes")
    }

    return response.json()
}