"use client"

import { getSession } from "next-auth/react"

export interface InvokeHistoryResponse {
    meta: {
        days: number
        limit: number
        guild_id?: string
        total: number
    }
    items: {
        guild: {
            id: string
            name: string
        }
        user_id: string
        command: {
            name: string
            category: string
        }
        timestamp: string
    }[]
    statistics: {
        total_commands: number
        unique_users: number
        active_guilds: number
        by_category: Record<string, number>
        daily: {
            date: string
            commands: Record<string, number>
        }[]
    }
}

interface ErrorResponse {
    error: string
}

export async function fetchInvokeHistory(): Promise<InvokeHistoryResponse> {
    const session = await getSession()
    console.log("Session:", session)
    if (!session) {
        throw new Error("Unauthorized")
    }

    const response = await fetch("https://api.evict.bot/invoke-history", {
        headers: {
            Authorization: `Bearer ${session.user.userToken}`,
            "Content-Type": "application/json"
        }
    })

    if (!response.ok) {
        const error = (await response.json()) as ErrorResponse
        throw new Error(error.error || "Failed to fetch invoke history")
    }

    const data = await response.json()
    return data as InvokeHistoryResponse
}
