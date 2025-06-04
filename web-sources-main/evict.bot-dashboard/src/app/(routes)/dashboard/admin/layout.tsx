"use client"

import { navigation } from "@/libs/dashboard/adminNavigation"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Bell, Menu, X } from "lucide-react"
import Image from "next/image"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState } from "react"
import UserAvatar from "@/components/UserAvatar"

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000 * 60 * 5,
            gcTime: 1000 * 60 * 30,
            refetchOnWindowFocus: false,
            retry: 1
        }
    }
})

export default function AdminDashboardLayout({
    children
}: {
    children: React.ReactNode
}) {
    return (
        <QueryClientProvider client={queryClient}>
            <DashboardLayoutContent>{children}</DashboardLayoutContent>
        </QueryClientProvider>
    )
}

function DashboardLayoutContent({
    children
}: {
    children: React.ReactNode
}) {
    const pathname = usePathname()
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)

    return (
        <div className="min-h-screen bg-[#0B0C0C]">
            <div className="bg-[#0B0C0C] w-full h-[70px] border-b border-white/5 shrink-0">
                <div className="h-full px-6 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            className="lg:hidden text-white/60 hover:text-white transition-colors">
                            {isSidebarOpen ? (
                                <X className="w-5 h-5" />
                            ) : (
                                <Menu className="w-5 h-5" />
                            )}
                        </button>

                        <Link href="/" className="flex items-center gap-3">
                            <Image
                                src="https://r2.evict.bot/evict-new.png"
                                alt="evict"
                                width={32}
                                height={32}
                                className="rounded-lg"
                            />
                            <span className="text-xl font-semibold text-white">evict</span>
                        </Link>
                    </div>

                    <div className="flex items-center gap-6">
                        <button className="text-white/60 hover:text-white transition-colors">
                            <Bell className="w-5 h-5" />
                        </button>
                        <UserAvatar />
                    </div>
                </div>
            </div>

            <div className="flex">
                <aside
                    className={`fixed lg:static inset-y-[70px] left-0 w-64 bg-[#0A0A0B] border-r border-white/5 
                    ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"} transition-transform duration-200`}>
                    <div className={`${!isSidebarOpen ? "lg:hidden" : ""} h-full`}>
                        <button
                            onClick={() => setIsSidebarOpen(false)}
                            className="absolute right-2 top-2 p-2 hover:bg-white/5 rounded-lg transition-colors lg:hidden">
                            <X className="w-5 h-5 text-white/60" />
                        </button>

                        <nav className="mt-4 px-3">
                            {Object.entries(navigation).map(([category, items]) => (
                                <div key={category} className="mb-6">
                                    <h4 className="px-3 mb-2 text-xs font-medium text-white/40 uppercase tracking-wider">
                                        {category}
                                    </h4>
                                    <div className="space-y-1">
                                        {items.map(item => (
                                            <Link
                                                key={item.name}
                                                href={`/dashboard/admin${item.href}`}
                                                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
                                                    ${pathname === `/dashboard/admin${item.href}`
                                                        ? "bg-white/10 text-white"
                                                        : "text-white/60 hover:text-white hover:bg-white/5"
                                                    }`}>
                                                <item.icon className="w-4 h-4" />
                                                <span>{item.name}</span>
                                            </Link>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </nav>
                    </div>
                </aside>

                <main className="flex-1 min-h-[calc(100vh-70px)]">
                    <div className="p-6">{children}</div>
                </main>
            </div>
        </div>
    )
} 