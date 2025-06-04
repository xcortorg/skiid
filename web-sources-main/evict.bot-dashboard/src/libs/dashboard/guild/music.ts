export interface ErrorResponse {
    error: string;
}

export async function fetchGuildMusic(guildId: string) {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/audio`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-GUILD-ID': guildId,
        }
    })

    if (!response.ok) {
        const error = await response.json() as ErrorResponse
        throw new Error(error.error || 'Failed to fetch music data')
    }

    const data = await response.json()
    return data
} 