"use client"

import { manageNotifications, type Notification } from "@/libs/dashboard/adminNotifications"
import { useMutation, useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import { AlertTriangle, Check, Info, Trash2, X } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

export default function Notifications() {
    const router = useRouter()
    const [title, setTitle] = useState("")
    const [content, setContent] = useState("")
    const [type, setType] = useState<"info" | "warning" | "error" | "success">("info")
    const [userId, setUserId] = useState("")
    const [expiresAt, setExpiresAt] = useState("")

    const { data: notifications, refetch } = useQuery({
        queryKey: ["notifications"],
        queryFn: () => manageNotifications({ action: "list" })
    })

    const { mutate: createNotification, isPending: isCreating } = useMutation({
        mutationFn: () => manageNotifications({
            action: "create",
            title,
            content,
            type,
            user_id: userId || undefined,
            expires_at: expiresAt || undefined
        }),
        onSuccess: () => {
            refetch()
            setTitle("")
            setContent("")
            setUserId("")
            setExpiresAt("")
        }
    })

    const { mutate: deleteNotification } = useMutation({
        mutationFn: (id: string) => manageNotifications({
            action: "delete",
            id
        }),
        onSuccess: () => refetch()
    })

    const getIcon = (type: string) => {
        switch (type) {
            case "info": return <Info className="w-4 h-4 text-blue-400" />
            case "warning": return <AlertTriangle className="w-4 h-4 text-yellow-400" />
            case "error": return <X className="w-4 h-4 text-red-400" />
            case "success": return <Check className="w-4 h-4 text-green-400" />
            default: return null
        }
    }

    return (
        <div>
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-white">Notifications</h1>
                <p className="text-white/60 mt-2">Manage system notifications</p>
            </div>

            <div className="bg-[#0A0A0B] rounded-xl border border-white/5 p-6">
                <form onSubmit={(e) => {
                    e.preventDefault()
                    createNotification()
                }} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-white/60 mb-2">Title</label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className="w-full bg-black/20 text-sm rounded-lg px-4 h-[38px] border border-white/5 focus:outline-none focus:border-white/10 text-white"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-white/60 mb-2">Content</label>
                        <textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            className="w-full bg-black/20 text-sm rounded-lg px-4 py-2 border border-white/5 focus:outline-none focus:border-white/10 text-white"
                            rows={3}
                            required
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-white/60 mb-2">Type</label>
                            <select
                                value={type}
                                onChange={(e) => setType(e.target.value as any)}
                                className="w-full bg-black/20 text-sm rounded-lg px-4 h-[38px] border border-white/5 focus:outline-none focus:border-white/10 text-white"
                            >
                                <option value="info">Info</option>
                                <option value="warning">Warning</option>
                                <option value="error">Error</option>
                                <option value="success">Success</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-white/60 mb-2">User ID (Optional)</label>
                            <input
                                type="text"
                                value={userId}
                                onChange={(e) => setUserId(e.target.value)}
                                className="w-full bg-black/20 text-sm rounded-lg px-4 h-[38px] border border-white/5 focus:outline-none focus:border-white/10 text-white"
                                placeholder="Leave empty for global"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-white/60 mb-2">Expires At (Optional)</label>
                            <input
                                type="datetime-local"
                                value={expiresAt}
                                onChange={(e) => setExpiresAt(e.target.value)}
                                className="w-full bg-black/20 text-sm rounded-lg px-4 h-[38px] border border-white/5 focus:outline-none focus:border-white/10 text-white"
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={isCreating}
                        className="px-4 py-2 bg-white/5 hover:bg-white/10 disabled:opacity-50 disabled:hover:bg-white/5 text-white rounded-lg"
                    >
                        Create Notification
                    </button>
                </form>

                <div className="mt-8">
                    <h3 className="text-lg font-medium text-white mb-4">Active Notifications</h3>
                    <div className="space-y-4">
                        {notifications?.notifications?.map((notification: Notification) => (
                            <div key={notification.id} className="bg-black/20 rounded-lg p-4">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-2">
                                        {getIcon(notification.type)}
                                        <h4 className="text-white font-medium">{notification.title}</h4>
                                    </div>
                                    <button
                                        onClick={() => deleteNotification(notification.id)}
                                        className="text-white/60 hover:text-white"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                                <p className="text-white/80 mt-2">{notification.content}</p>
                                <div className="flex gap-4 mt-2 text-sm text-white/60">
                                    {notification.user_id && (
                                        <span>User: {notification.user_id}</span>
                                    )}
                                    {notification.expires_at && (
                                        <span>Expires: {format(new Date(notification.expires_at), "MMM d, yyyy HH:mm")}</span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
} 