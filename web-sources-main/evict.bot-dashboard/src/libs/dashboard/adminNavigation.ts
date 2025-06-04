import {
    Hash,
    Search,
    User,
    Database,
    LayoutGrid,
    Settings2,
    Shield,
    Users,
    Server,
    FolderSearch,
    Bell
} from "lucide-react"

export const navigation = {
    GENERAL: [
        { name: "Invokes", icon: Hash, href: "" },
        { name: "Server Lookup", icon: Search, href: "/server-lookup" },
        { name: "User Lookup", icon: User, href: "/user-lookup", comingSoon: true },
        { name: "Notifications", icon: Bell, href: "/notifications" }
    ],
    SERVER: [
        { name: "Fetch Guild Settings", icon: Database, href: "/guild-settings", comingSoon: true },
        { name: "Roles & Channels", icon: LayoutGrid, href: "/roles-channels", comingSoon: true },
    ],
    MANAGEMENT: [
        { name: "Bot Settings", icon: Settings2, href: "/bot-settings", comingSoon: true },
        { name: "Permissions", icon: Shield, href: "/permissions", comingSoon: true },
        { name: "Staff", icon: Users, href: "/staff", comingSoon: true },
        { name: "Servers", icon: Server, href: "/servers", comingSoon: true },
        { name: "Logs", icon: FolderSearch, href: "/logs", comingSoon: true }
    ]
}
