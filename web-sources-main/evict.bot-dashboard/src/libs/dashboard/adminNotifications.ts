import { getSession } from "next-auth/react"

export interface Notification {
    id: string
    title: string
    content: string
    type: "info" | "warning" | "error" | "success"
    user_id: string | null
    expires_at: string | null
    created_at: string
}

interface NotificationCreatePayload {
    action: "create"
    title: string
    content: string
    type: "info" | "warning" | "error" | "success"
    user_id?: string
    expires_at?: string
}

interface NotificationEditPayload {
    action: "edit"
    id: string
    title: string
    content: string
}

interface NotificationDeletePayload {
    action: "delete"
    id: string
}

interface NotificationListPayload {
    action: "list"
}

type NotificationPayload = 
    | NotificationCreatePayload 
    | NotificationEditPayload 
    | NotificationDeletePayload 
    | NotificationListPayload

export async function manageNotifications(payload: NotificationPayload): Promise<{ notifications?: Notification[], success: boolean }> {
    const session = await getSession()
    if (!session) {
        throw new Error("403")
    }

    const response = await fetch("https://api.evict.bot/notifications/manage", {
        method: "POST",
        headers: {
            Authorization: `Bearer ${session.user.userToken}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    })

    if (!response.ok) {
        if (response.status === 403) {
            throw new Error("403")
        }
        throw new Error("Failed to manage notifications")
    }

    return response.json()
} 