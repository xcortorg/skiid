import { getSession } from "next-auth/react"

export interface DiscordUser {
    id: string
    username: string
    avatar: string | null
    discriminator: string
    public_flags: number
    flags: number
    banner: string | null
    accent_color: number | null
    global_name: string | null
    avatar_decoration_data: {
        asset: string
        sku_id: string
    } | null
    banner_color: string | null
    mfa_enabled: boolean
    locale: string
    premium_type: number
    email: string | null
    verified: boolean
}

export interface Instance {
    id: string
    status: 'active' | 'cancelled' | 'expired' | 'pending'
    expires_at: string | null
    purchased_at: string | null
    email: string
}

export interface DashboardUserResponse {
    success: boolean
    user: DiscordUser
    donator: boolean
    instance: Instance | null
}

export interface APIError {
    error: string
}

export async function fetchDashboardUser(): Promise<DashboardUserResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch("https://api.evict.bot/dashboard/user", {
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
        }
    })

    if (response.status === 401) {
        throw new Error("Session expired")
    }

    if (!response.ok) {
        const error: APIError = await response.json()
        throw new Error(error.error || "Failed to fetch user data")
    }

    return response.json()
} 