interface ModerationAction {
    [key: string]: number
}

interface DailyStatistic {
    date: string
    commands_used: number
    messages_sent: number
    voice_minutes: number
    moderation: ModerationAction
}

export interface GuildStatistics {
    guild_id: string
    days: number
    statistics: DailyStatistic[]
}

export interface StatisticsResponse extends GuildStatistics {
    success: boolean
    data: GuildStatistics
}

export async function fetchGuildStatistics(guildId: string, days: number = 7): Promise<StatisticsResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/statistics`, {
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            "X-GUILD-ID": guildId,
            "X-DAYS": days.toString()
        }
    })

    if (response.status === 401) {
        throw new Error("Unauthorized")
    }

    if (response.status === 403) {
        throw new Error("Missing required permissions or bot not in server")
    }

    if (!response.ok) {
        throw new Error("Failed to fetch statistics")
    }

    return response.json()
}

export function getTotalModerationActions(statistics: DailyStatistic[], type: string): number {
    return statistics.reduce((total, day) => total + (day.moderation[type] || 0), 0)
}

export function getModerationTypes(statistics: DailyStatistic[]): string[] {
    const types = new Set<string>()
    statistics.forEach(day => {
        Object.keys(day.moderation).forEach(type => types.add(type))
    })
    return Array.from(types)
}

export function getTotalStats(statistics: DailyStatistic[]) {
    return statistics.reduce((totals, day) => ({
        commands_used: totals.commands_used + day.commands_used,
        messages_sent: totals.messages_sent + day.messages_sent,
        voice_minutes: totals.voice_minutes + day.voice_minutes
    }), {
        commands_used: 0,
        messages_sent: 0,
        voice_minutes: 0
    })
}