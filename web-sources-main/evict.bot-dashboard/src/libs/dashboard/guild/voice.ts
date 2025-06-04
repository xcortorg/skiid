interface VoiceChannelMember {
    id: string;
    name: string;
    avatar: string;
    bot: boolean;
    speaking: boolean;
}

interface VoiceChannel {
    id: string;
    name: string;
    user_limit: number;
    member_count: number;
    is_private: boolean;
}

interface CurrentChannel {
    id: string;
    name: string;
    connected: boolean;
    listeners: VoiceChannelMember[];
}

interface VoiceInfo {
    current_channel: CurrentChannel;
    available_channels: VoiceChannel[];
}

interface ErrorResponse {
    error: string;
}

export async function fetchVoiceInfo(guildId: string): Promise<VoiceInfo> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch('https://api.evict.bot/voice', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-GUILD-ID': guildId
        }
    })

    if (!response.ok) {
        const error = await response.json() as ErrorResponse
        throw new Error(error.error || 'Failed to fetch voice info')
    }

    const data = await response.json()
    return data as VoiceInfo
} 