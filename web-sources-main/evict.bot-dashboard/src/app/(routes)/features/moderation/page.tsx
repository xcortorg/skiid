"use client"

import { motion } from "framer-motion"
import {
    AlertTriangle,
    Ban,
    Bot,
    History,
    Lock,
    MessageSquare,
    Shield,
    Trash2,
    UserX
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { RiDiscordLine, RiRobot2Line } from "react-icons/ri"

const Switch = ({
    checked,
    onChange
}: {
    checked: boolean
    onChange: (checked: boolean) => void
}) => {
    return (
        <button
            onClick={() => onChange(!checked)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                checked ? "bg-evict-pink" : "bg-white/10"
            }`}>
            <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    checked ? "translate-x-5" : "translate-x-1"
                }`}
            />
        </button>
    )
}

export default function ModerationFeature() {
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const [activeTab, setActiveTab] = useState<"antinuke" | "raid" | "spam">("antinuke")
    const [configs, setConfigs] = useState({
        antinuke: { threshold: 5, time: 10, punishment: "ban" },
        raid: { threshold: 10, time: 30, punishment: "kick" },
        spam: { threshold: 3, time: 15, punishment: "strip" }
    })
    const [demoMessages, setDemoMessages] = useState<Array<any>>([])
    const [messages, setMessages] = useState<
        Array<{
            id: string
            content: string
            author: string
            timestamp: Date
            deleted?: boolean
            warned?: boolean
            filtered?: boolean
        }>
    >([
        {
            id: "1",
            content: "Hey everyone!",
            author: "User123",
            timestamp: new Date()
        }
    ])
    const [isSimulating, setIsSimulating] = useState(false)
    const [selectedPreset, setSelectedPreset] = useState<"strict" | "medium" | "relaxed">("medium")
    const [showAdvanced, setShowAdvanced] = useState(false)
    const [modLogs, setModLogs] = useState([
        {
            caseNumber: "293",
            type: "ban",
            user: { id: "214753146512080997", name: "resent" },
            moderator: { id: "1332327503062106154", name: "x14c" },
            reason: "No reason provided",
            timestamp: "02/01/2025, 23:31"
        },
        {
            caseNumber: "292",
            type: "role add",
            user: { id: "108220605721398864", name: "1o9s_" },
            moderator: { id: "1332327503062106154", name: "x14c" },
            reason: "Added by x14c (1332327503062106154)",
            timestamp: "02/01/2025, 23:15"
        },
        {
            caseNumber: "291",
            type: "role add",
            user: { id: "114030134571126510", name: "cv3zy" },
            moderator: { id: "1332327503062106154", name: "x14c" },
            reason: "Added by x14c (1332327503062106154)",
            timestamp: "02/01/2025, 15:33"
        }
    ])
    const [jailLogs, setJailLogs] = useState([
        {
            caseNumber: "295",
            type: "jail",
            user: { id: "214753146512080997", name: "resent", avatar: "/resent.png" },
            moderator: { id: "1332327503062106154", name: "x14c" },
            reason: "Spamming in general",
            duration: "24h",
            timestamp: "02/01/2025, 23:31"
        },
        {
            caseNumber: "294",
            type: "jail",
            user: { id: "108220605721398864", name: "1o9s_", avatar: "/adam.png" },
            moderator: { id: "1332327503062106154", name: "x14c" },
            reason: "Inappropriate content",
            duration: "12h",
            timestamp: "02/01/2025, 23:15"
        }
    ])

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "end"
        })
    }

    useEffect(() => {
        if (messages.length > 0) {
            const messagesContainer = messagesEndRef.current?.parentElement
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight
            }
        }
    }, [messages])

    useEffect(() => {
        if (demoMessages.length > 0) {
            const container = document.querySelector(".messages-container")
            container?.scrollTo({
                top: container.scrollHeight,
                behavior: "smooth"
            })
        }
    }, [demoMessages])

    const demoScenarios = {
        spam: {
            title: "Spam Detection & Prevention",
            description: "See how Evict automatically detects and prevents spam messages",
            action: () => {
                const spamMessages = [
                    "CLICK HERE FOR FEMBOY THIGHS",
                    "FREE NITRO CLICK NOW!",
                    "DISCORD NITRO GIVEAWAY!",
                    "CLICK FOR FREE NITRO!"
                ]

                let delay = 800
                spamMessages.forEach((msg, i) => {
                    setTimeout(() => {
                        setMessages(prev => [
                            ...prev,
                            {
                                id: Date.now().toString() + i,
                                content: msg,
                                author: "SpamBot",
                                timestamp: new Date(),
                                filtered: true
                            }
                        ])
                    }, delay)
                    delay += 800
                })

                setTimeout(() => {
                    setMessages(prev => [
                        ...prev,
                        {
                            id: "system",
                            content: "⚠️ Spam detected! User has been automatically muted.",
                            author: "System",
                            timestamp: new Date()
                        }
                    ])
                }, delay + 800)
            }
        },
        raid: {
            title: "Raid Protection System",
            description: "Watch the raid protection system identify and stop potential raids",
            action: () => {
                let delay = 800
                for (let i = 0; i < 5; i++) {
                    setTimeout(() => {
                        setMessages(prev => [
                            ...prev,
                            {
                                id: Date.now().toString() + i,
                                content: "I just joined!",
                                author: `RaidUser${i}`,
                                timestamp: new Date(),
                                warned: true
                            }
                        ])
                    }, delay)
                    delay += 600
                }

                setTimeout(() => {
                    setMessages(prev => [
                        ...prev,
                        {
                            id: "system",
                            content: "🛡️ Raid detected! Server has been automatically locked down.",
                            author: "System",
                            timestamp: new Date()
                        }
                    ])
                }, delay + 800)
            }
        },
        antinuke: {
            title: "Anti-Nuke Protection",
            description: "See how Evict protects against server nuking attempts",
            action: () => {
                setMessages([
                    {
                        id: "1",
                        content: "Server activity monitoring started...",
                        author: "System",
                        timestamp: new Date()
                    }
                ])

                let delay = 800
                for (let i = 0; i < 3; i++) {
                    setTimeout(() => {
                        setMessages(prev => [
                            ...prev,
                            {
                                id: Date.now().toString() + i,
                                content: "🗑️ #general-" + (i + 1) + " was deleted",
                                author: "Malicious User",
                                timestamp: new Date(),
                                warned: true
                            }
                        ])
                    }, delay)
                    delay += 600
                }

                setTimeout(() => {
                    setMessages(prev => [
                        ...prev,
                        {
                            id: "system-1",
                            content:
                                "⚠️ Suspicious Activity Detected: Multiple channels deleted in quick succession",
                            author: "System",
                            timestamp: new Date()
                        }
                    ])
                }, delay)

                setTimeout(() => {
                    setMessages(prev => [
                        ...prev,
                        {
                            id: "system-2",
                            content:
                                "🛡️ Anti-Nuke Triggered: Channel deletion threshold exceeded (3/5 in 10s)",
                            author: "System",
                            timestamp: new Date()
                        }
                    ])
                }, delay + 800)

                setTimeout(() => {
                    setMessages(prev => [
                        ...prev,
                        {
                            id: "system-3",
                            content: "⚡ Action Taken: Dangerous permissions stripped from user",
                            author: "System",
                            timestamp: new Date()
                        }
                    ])
                }, delay + 1600)
            }
        }
    }

    const updateConfig = (tab: "antinuke" | "raid" | "spam", key: string, value: any) => {
        setConfigs(prev => ({
            ...prev,
            [tab]: {
                ...prev[tab],
                [key]: value
            }
        }))
    }

    const presets = {
        strict: {
            antinuke: { threshold: 3, time: 5, punishment: "ban" },
            raid: { threshold: 5, time: 15, punishment: "ban" },
            spam: { threshold: 2, time: 10, punishment: "ban" }
        },
        medium: {
            antinuke: { threshold: 5, time: 10, punishment: "kick" },
            raid: { threshold: 10, time: 30, punishment: "kick" },
            spam: { threshold: 3, time: 15, punishment: "strip" }
        },
        relaxed: {
            antinuke: { threshold: 8, time: 20, punishment: "strip" },
            raid: { threshold: 15, time: 45, punishment: "kick" },
            spam: { threshold: 5, time: 30, punishment: "strip" }
        }
    }

    const simulateAttack = async (type: "antinuke" | "raid" | "spam") => {
        if (isSimulating) return
        setIsSimulating(true)
        setDemoMessages([])
        const config = configs[type as keyof typeof configs]

        const getActionMessage = (type: string, count: number) => {
            switch (type) {
                case "channel":
                    return `🗑️ #general-${count} was deleted by Malicious User`
                case "role":
                    return `👥 @Admin-${count} role was deleted by Malicious User`
                case "bot":
                    return `🤖 SuspiciousBot-${count} was added by Malicious User`
                default:
                    return `Action ${count}`
            }
        }

        const getPunishmentMessage = (punishment: string) => {
            switch (punishment) {
                case "strip":
                    return "🛡️ Action Taken: Dangerous permissions stripped from user"
                case "kick":
                    return "👢 Action Taken: User has been kicked from the server"
                case "ban":
                    return "🔨 Action Taken: User has been banned from the server"
                default:
                    return "Action taken"
            }
        }

        let delay = 0
        for (let i = 0; i < config.threshold + 1; i++) {
            setTimeout(() => {
                setDemoMessages(prev => [
                    ...prev,
                    {
                        type: "action",
                        content:
                            type === "antinuke"
                                ? `🗑️ #general-${i + 1} was deleted by Malicious User`
                                : type === "raid"
                                  ? `👥 @Admin-${i + 1} role was deleted by Malicious User`
                                  : `🤖 SuspiciousBot-${i + 1} was added by Malicious User`
                    }
                ])
            }, delay)
            delay += 500
        }

        setTimeout(() => {
            setDemoMessages(prev => [
                ...prev,
                {
                    type: "warning",
                    content: `⚠️ Anti-Nuke Triggered: ${type} threshold exceeded (${config.threshold + 1}/${config.threshold} in ${config.time}s)`
                }
            ])
        }, delay)

        setTimeout(() => {
            setDemoMessages(prev => [
                ...prev,
                {
                    type: "system",
                    content:
                        config.punishment === "strip"
                            ? "🛡️ Action Taken: Dangerous permissions stripped from user"
                            : config.punishment === "kick"
                              ? "👢 Action Taken: User has been kicked from the server"
                              : "🔨 Action Taken: User has been banned from the server"
                }
            ])
        }, delay + 500)

        setTimeout(() => {
            setIsSimulating(false)
        }, delay + 1000)
    }

    const tabs = [
        { key: "antinuke", title: "Channel Deletions", icon: <Trash2 className="w-4 h-4" /> },
        { key: "raid", title: "Role Updates", icon: <Shield className="w-4 h-4" /> },
        { key: "spam", title: "Bot Additions", icon: <Bot className="w-4 h-4" /> }
    ]

    return (
        <div className="min-h-screen bg-gradient-to-b from-[#0A0A0B] to-black">
            <div className="relative border-b border-white/5">
                <div className="absolute inset-0 bg-[url('/noise.png')] opacity-5" />
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-24 relative">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8 }}
                        className="text-center">
                        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 md:mb-6">
                            <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-300">
                                Advanced Moderation
                            </span>
                        </h1>
                        <p className="text-base sm:text-lg text-gray-400 max-w-3xl mx-auto px-4">
                            Keep your server safe with powerful moderation tools, automated systems,
                            and detailed logging
                        </p>
                    </motion.div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mb-12 md:mb-20">
                    {[
                        {
                            icon: <Shield className="w-6 h-6 text-evict-pink" />,
                            title: "Auto-Moderation",
                            description:
                                "Automatically detect and handle spam, inappropriate content, and raids"
                        },
                        {
                            icon: <MessageSquare className="w-6 h-6 text-evict-pink" />,
                            title: "Message Filtering",
                            description:
                                "Filter unwanted content, links, and attachments with customizable rules"
                        },
                        {
                            icon: <UserX className="w-6 h-6 text-evict-pink" />,
                            title: "User Management",
                            description: "Comprehensive tools for warnings, mutes, kicks, and bans"
                        },
                        {
                            icon: <History className="w-6 h-6 text-evict-pink" />,
                            title: "Detailed Logging",
                            description:
                                "Track all moderation actions with comprehensive audit logs"
                        },
                        {
                            icon: <AlertTriangle className="w-6 h-6 text-evict-pink" />,
                            title: "Raid Protection",
                            description: "Advanced algorithms to detect and prevent raid attempts"
                        },
                        {
                            icon: <Ban className="w-6 h-6 text-evict-pink" />,
                            title: "Auto-Punishments",
                            description: "Automated escalating punishments for repeat offenders"
                        }
                    ].map((feature, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="group relative bg-white/[0.02] border border-white/5 rounded-xl p-6 hover:border-white/10 
                                     transition-all duration-300 overflow-hidden">
                            <div className="relative z-10">
                                <div className="p-3 bg-white/5 rounded-xl w-fit mb-4">
                                    {feature.icon}
                                </div>
                                <h3 className="text-xl font-semibold text-white mb-2">
                                    {feature.title}
                                </h3>
                                <p className="text-white/60">{feature.description}</p>
                            </div>
                            <div
                                className="absolute inset-0 bg-gradient-to-br from-evict-pink/5 to-transparent 
                                          opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                            />
                        </motion.div>
                    ))}
                </div>

                <div className="mb-12 md:mb-20">
                    <motion.div
                        key={activeTab}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden max-w-7xl mx-auto">
                        <div className="border-b border-white/5 p-4 md:p-6">
                            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
                                Anti-Nuke Configuration
                            </h2>
                            <p className="text-white/60 text-sm md:text-base">
                                Configure protection against destructive actions
                            </p>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2">
                            <div className="bg-black/20">
                                <div className="border-b border-white/5">
                                    <div className="flex">
                                        {tabs.map(tab => (
                                            <button
                                                key={tab.key}
                                                onClick={() =>
                                                    setActiveTab(
                                                        tab.key as "antinuke" | "raid" | "spam"
                                                    )
                                                }
                                                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors
                                                    ${
                                                        activeTab === tab.key
                                                            ? "text-white border-b-2 border-evict-pink"
                                                            : "text-white/40 hover:text-white/60"
                                                    }`}>
                                                <div className="p-2 bg-white/5 rounded-xl w-fit">
                                                    {tab.icon}
                                                </div>
                                                {tab.title}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="p-6">
                                    <div className="border-b border-white/5 p-4 bg-black/20">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="flex items-center gap-2">
                                                <Switch
                                                    checked={showAdvanced}
                                                    onChange={setShowAdvanced}
                                                />
                                                <span className="text-sm text-white/60">
                                                    Advanced Settings
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {["relaxed", "medium", "strict"].map(preset => (
                                                    <button
                                                        key={preset}
                                                        onClick={() => {
                                                            setSelectedPreset(
                                                                preset as
                                                                    | "strict"
                                                                    | "medium"
                                                                    | "relaxed"
                                                            )
                                                            setConfigs(
                                                                presets[
                                                                    preset as keyof typeof presets
                                                                ]
                                                            )
                                                        }}
                                                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                                            selectedPreset === preset
                                                                ? "bg-evict-pink text-white"
                                                                : "bg-white/5 text-white/60 hover:bg-white/10"
                                                        }`}>
                                                        {preset.charAt(0).toUpperCase() +
                                                            preset.slice(1)}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        {showAdvanced && (
                                            <div className="grid grid-cols-2 gap-4 mt-4">
                                                <div className="bg-black/20 rounded-lg p-3">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <span className="text-white/60 text-sm">
                                                            Risk Level
                                                        </span>
                                                        <span
                                                            className={`text-sm font-medium ${
                                                                selectedPreset === "strict"
                                                                    ? "text-red-400"
                                                                    : selectedPreset === "medium"
                                                                      ? "text-yellow-400"
                                                                      : "text-green-400"
                                                            }`}>
                                                            {selectedPreset === "strict"
                                                                ? "High"
                                                                : selectedPreset === "medium"
                                                                  ? "Medium"
                                                                  : "Low"}
                                                        </span>
                                                    </div>
                                                    <div className="h-1 bg-white/5 rounded-full">
                                                        <div
                                                            className={`h-full rounded-full transition-all duration-300 ${
                                                                selectedPreset === "strict"
                                                                    ? "w-full bg-red-400"
                                                                    : selectedPreset === "medium"
                                                                      ? "w-2/3 bg-yellow-400"
                                                                      : "w-1/3 bg-green-400"
                                                            }`}
                                                        />
                                                    </div>
                                                </div>

                                                <div className="bg-black/20 rounded-lg p-3">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <span className="text-white/60 text-sm">
                                                            Effectiveness
                                                        </span>
                                                        <span className="text-sm font-medium text-evict-pink">
                                                            {selectedPreset === "strict"
                                                                ? "98%"
                                                                : selectedPreset === "medium"
                                                                  ? "85%"
                                                                  : "70%"}
                                                        </span>
                                                    </div>
                                                    <div className="h-1 bg-white/5 rounded-full">
                                                        <div
                                                            className="h-full rounded-full bg-evict-pink transition-all duration-300"
                                                            style={{
                                                                width:
                                                                    selectedPreset === "strict"
                                                                        ? "98%"
                                                                        : selectedPreset ===
                                                                            "medium"
                                                                          ? "85%"
                                                                          : "70%"
                                                            }}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    <div className="space-y-6">
                                        <div className="flex items-center justify-between">
                                            <span className="text-white/60">Threshold</span>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() =>
                                                        updateConfig(
                                                            activeTab,
                                                            "threshold",
                                                            configs[activeTab].threshold - 1
                                                        )
                                                    }
                                                    className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-white flex items-center justify-center">
                                                    -
                                                </button>
                                                <span className="w-12 text-center text-white">
                                                    {configs[activeTab].threshold}
                                                </span>
                                                <button
                                                    onClick={() =>
                                                        updateConfig(
                                                            activeTab,
                                                            "threshold",
                                                            configs[activeTab].threshold + 1
                                                        )
                                                    }
                                                    className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-white flex items-center justify-center">
                                                    +
                                                </button>
                                            </div>
                                        </div>

                                        <div className="space-y-2">
                                            <div className="flex items-center justify-between">
                                                <span className="text-white/60">Time Window</span>
                                                <span className="text-white">
                                                    {configs[activeTab].time}s
                                                </span>
                                            </div>
                                            <input
                                                type="range"
                                                min="5"
                                                max="60"
                                                value={configs[activeTab].time}
                                                onChange={e =>
                                                    updateConfig(
                                                        activeTab,
                                                        "time",
                                                        parseInt(e.target.value)
                                                    )
                                                }
                                                className="w-full accent-evict-pink appearance-none bg-white/5 h-1 rounded-lg focus:outline-none"
                                                style={{
                                                    WebkitAppearance: "none",
                                                    background: "rgba(255, 255, 255, 0.05)"
                                                }}
                                            />
                                        </div>

                                        <div>
                                            <span className="text-white/60 block mb-2">
                                                Punishment
                                            </span>
                                            <div className="flex gap-2">
                                                {["strip", "kick", "ban"].map(p => (
                                                    <button
                                                        key={p}
                                                        onClick={() =>
                                                            updateConfig(activeTab, "punishment", p)
                                                        }
                                                        className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                                                            configs[activeTab].punishment === p
                                                                ? "bg-evict-pink text-white"
                                                                : "bg-white/5 text-white/60 hover:bg-white/10"
                                                        }`}>
                                                        {p}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        <button
                                            onClick={() => simulateAttack(activeTab)}
                                            className="w-full py-2.5 bg-white/5 hover:bg-white/10 text-white/80 
                                                     hover:text-white rounded-lg transition-all duration-200 font-medium"
                                            disabled={isSimulating}>
                                            Test Protection
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-black/20 flex flex-col h-[400px] border-l border-white/5">
                                <div className="border-b border-white/5 p-4">
                                    <h3 className="text-white font-medium">Live Preview</h3>
                                    <p className="text-sm text-white/40">
                                        See your configuration in action
                                    </p>
                                </div>
                                <div className="flex-1 p-4 overflow-y-auto messages-container">
                                    <div className="space-y-2">
                                        {demoMessages.map((msg, i) => (
                                            <motion.div
                                                key={i}
                                                initial={{ opacity: 0, y: 10 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ duration: 0.2 }}
                                                className={`p-3 rounded-lg transition-all duration-200 hover:bg-white/[0.03] group ${
                                                    msg.type === "system"
                                                        ? "bg-evict-pink/10 text-evict-pink border border-evict-pink/10"
                                                        : msg.type === "warning"
                                                          ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/10"
                                                          : "bg-white/[0.02] text-white/60 border border-white/5"
                                                }`}>
                                                <div className="flex items-center gap-2">
                                                    <motion.div
                                                        initial={{ scale: 0.8 }}
                                                        animate={{ scale: 1 }}
                                                        transition={{
                                                            type: "spring",
                                                            stiffness: 200,
                                                            damping: 10
                                                        }}>
                                                        {msg.type === "action" && (
                                                            <Trash2 className="w-4 h-4 text-white/40" />
                                                        )}
                                                        {msg.type === "warning" && (
                                                            <AlertTriangle className="w-4 h-4 text-yellow-400" />
                                                        )}
                                                        {msg.type === "system" && (
                                                            <Shield className="w-4 h-4 text-evict-pink" />
                                                        )}
                                                    </motion.div>
                                                    <span>{msg.content}</span>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>

                <div className="max-w-8xl mx-auto py-12 ">
                    <div className="mb-12">
                        <h1 className="text-4xl font-bold text-white mb-4">Action Logs</h1>
                        <p className="text-lg text-white/60">
                            View and manage all moderation actions across your server
                        </p>
                    </div>

                    <div className="grid grid-cols-1 gap-6 mb-6">
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden col-span-1">
                            <div className="border-b border-white/5 p-4 md:p-6">
                                <h2 className="text-xl font-bold text-white">Jail Logs</h2>
                                <p className="text-sm text-white/60">Regular format</p>
                            </div>
                            <div className="divide-y divide-white/5">
                                {jailLogs.map(log => (
                                    <div
                                        key={log.caseNumber}
                                        className="p-4 md:p-6 hover:bg-white/[0.02] transition-colors">
                                        <div className="flex items-start gap-3">
                                            <div className="shrink-0 w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
                                                <Lock className="w-4 h-4 text-orange-400" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-white font-medium">
                                                        Case #{log.caseNumber}
                                                    </span>
                                                    <span className="text-xs px-1.5 py-0.5 rounded-md bg-orange-500/10 text-orange-400">
                                                        jail
                                                    </span>
                                                    <span className="text-xs px-1.5 py-0.5 rounded-md bg-white/5 text-white/60">
                                                        {log.duration}
                                                    </span>
                                                </div>
                                                <div className="grid gap-1 text-sm">
                                                    <div className="text-white/60">
                                                        <span className="font-medium">User:</span>{" "}
                                                        {log.user.name} ({log.user.id})
                                                    </div>
                                                    <div className="text-white/60">
                                                        <span className="font-medium">
                                                            Moderator:
                                                        </span>{" "}
                                                        {log.moderator.name} ({log.moderator.id})
                                                    </div>
                                                    <div className="text-white/60">
                                                        <span className="font-medium">Reason:</span>{" "}
                                                        {log.reason}
                                                    </div>
                                                    <div className="text-white/40 text-xs">
                                                        {log.timestamp}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    </div>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-4 md:p-6">
                            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
                                Moderation Logs
                            </h2>
                            <p className="text-white/60 text-sm md:text-base">
                                Detailed history of all moderation actions
                            </p>
                        </div>
                        <div className="divide-y divide-white/5">
                            {modLogs.map(log => (
                                <div
                                    key={log.caseNumber}
                                    className="p-4 md:p-6 hover:bg-white/[0.02] transition-colors">
                                    <div className="flex items-start gap-3">
                                        <div className="shrink-0 w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
                                            {log.type === "ban" ? (
                                                <Ban className="w-4 h-4 text-red-400" />
                                            ) : log.type === "role add" ? (
                                                <Shield className="w-4 h-4 text-blue-400" />
                                            ) : (
                                                <AlertTriangle className="w-4 h-4 text-yellow-400" />
                                            )}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="text-white font-medium">
                                                    Case #{log.caseNumber}
                                                </span>
                                                <span
                                                    className={`text-xs px-1.5 py-0.5 rounded-md ${
                                                        log.type === "ban"
                                                            ? "bg-red-500/10 text-red-400"
                                                            : log.type === "role add"
                                                              ? "bg-blue-500/10 text-blue-400"
                                                              : "bg-yellow-500/10 text-yellow-400"
                                                    }`}>
                                                    {log.type}
                                                </span>
                                            </div>

                                            <div className="grid gap-1 text-sm">
                                                <div className="text-white/60">
                                                    <span className="font-medium">User:</span>{" "}
                                                    {log.user.name} ({log.user.id})
                                                </div>
                                                <div className="text-white/60">
                                                    <span className="font-medium">Moderator:</span>{" "}
                                                    {log.moderator.name} ({log.moderator.id})
                                                </div>
                                                <div className="text-white/60">
                                                    <span className="font-medium">Reason:</span>{" "}
                                                    {log.reason}
                                                </div>
                                                <div className="text-white/40 text-xs">
                                                    {log.timestamp}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                </div>

                <div className="mb-12 md:mb-20">
                    <motion.div
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-4 md:p-6">
                            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
                                Try it Yourself
                            </h2>
                            <p className="text-white/60 text-sm md:text-base">
                                Test different moderation scenarios in real-time
                            </p>
                        </div>

                        <div className="flex flex-col lg:flex-row">
                            <div className="lg:w-64 lg:border-r border-white/5 p-2 bg-black/20 space-y-2">
                                {Object.entries(demoScenarios).map(([key, scenario]) => (
                                    <div key={key}>
                                        <button
                                            onClick={() => {
                                                setActiveTab(key as "antinuke" | "raid" | "spam")
                                                scenario.action()
                                            }}
                                            className={`w-full text-left px-4 py-3 rounded-lg transition-all ${
                                                activeTab === key
                                                    ? "bg-evict-pink/20 text-white"
                                                    : "text-white/60 hover:bg-white/5"
                                            }`}>
                                            <div className="flex items-center gap-3">
                                                <div
                                                    className={`w-1.5 h-1.5 rounded-full ${
                                                        activeTab === key
                                                            ? "bg-evict-pink"
                                                            : "bg-white/20"
                                                    }`}
                                                />
                                                <span className="text-sm font-medium">
                                                    {scenario.title}
                                                </span>
                                            </div>
                                            <p className="text-xs text-white/40 ml-6 mt-1">
                                                {scenario.description}
                                            </p>
                                        </button>
                                    </div>
                                ))}
                            </div>

                            <div className="flex-1">
                                <div className="border-b border-white/5 bg-black/40 p-4">
                                    <h3 className="text-white font-medium mb-1">
                                        {
                                            demoScenarios[activeTab as keyof typeof demoScenarios]
                                                .title
                                        }
                                    </h3>
                                    <p className="text-sm text-white/60">
                                        {
                                            demoScenarios[activeTab as keyof typeof demoScenarios]
                                                .description
                                        }
                                    </p>
                                </div>
                                <div className="relative p-4 h-[400px] overflow-y-auto space-y-3 bg-black/20 scroll-smooth">
                                    <div className="absolute inset-0 bg-[url('/noise.png')] opacity-5 pointer-events-none" />
                                    {messages.map(message => (
                                        <motion.div
                                            key={message.id}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className={`group relative flex items-start gap-3 p-3 rounded-xl transition-all 
                                                ${message.filtered ? "opacity-50" : ""}
                                                ${
                                                    message.author === "System"
                                                        ? "bg-gradient-to-r from-evict-pink/10 to-transparent"
                                                        : "hover:bg-white/5"
                                                }`}>
                                            <div
                                                className={`shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br 
                                                ${
                                                    message.author === "System"
                                                        ? "from-evict-pink/20 to-evict-pink/5"
                                                        : "from-white/10 to-white/5"
                                                } 
                                                flex items-center justify-center`}>
                                                {message.author === "System" ? (
                                                    <Shield className="w-4 h-4 text-evict-pink" />
                                                ) : (
                                                    <MessageSquare className="w-4 h-4 text-white/40" />
                                                )}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span
                                                        className={`text-sm font-medium ${
                                                            message.author === "System"
                                                                ? "text-evict-pink"
                                                                : "text-white"
                                                        }`}>
                                                        {message.author}
                                                    </span>
                                                    <span className="text-xs px-1.5 py-0.5 rounded-md bg-white/5 text-white/40">
                                                        {new Date(
                                                            message.timestamp
                                                        ).toLocaleTimeString([], {
                                                            hour: "2-digit",
                                                            minute: "2-digit"
                                                        })}
                                                    </span>
                                                </div>
                                                <p
                                                    className={`text-sm break-words ${
                                                        message.author === "System"
                                                            ? "text-white/80"
                                                            : "text-white/60"
                                                    }`}>
                                                    {message.filtered && (
                                                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-red-500/10 text-red-400 text-xs font-medium mr-1">
                                                            <Trash2 className="w-3 h-3" />
                                                            Filtered
                                                        </span>
                                                    )}
                                                    {message.warned && (
                                                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-yellow-500/10 text-yellow-400 text-xs font-medium mr-1">
                                                            <AlertTriangle className="w-3 h-3" />
                                                            Warning
                                                        </span>
                                                    )}
                                                    {message.content}
                                                </p>
                                            </div>
                                        </motion.div>
                                    ))}
                                    <div ref={messagesEndRef} className="h-0" />
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>

                <div className="mb-12 md:mb-20">
                    <h2 className="text-2xl md:text-3xl font-bold text-white mb-4 md:mb-8">
                        Quick Setup Guide
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
                        {[
                            {
                                step: "1",
                                title: "Enable Ban Detection",
                                command: ";antinuke ban (status) (flags)",
                                description: "Enable detection for mass ban attempts"
                            },
                            {
                                step: "2",
                                title: "Set up moderation",
                                command: ";setme",
                                description: "Set up moderation channels such as mod logs"
                            },
                            {
                                step: "3",
                                title: "Block Links",
                                command:
                                    ";antiraid filter links ('invites', 'external' or 'all') (status) (flags)",
                                description: "Block invites, external links, or all links"
                            }
                        ].map((step, index) => (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.1 }}
                                className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                                <div className="text-evict-pink font-bold mb-2">
                                    Step {step.step}
                                </div>
                                <h3 className="text-xl font-semibold text-white mb-2">
                                    {step.title}
                                </h3>
                                <p className="text-white/60 mb-4">{step.description}</p>
                                <code className="block bg-black/20 px-4 py-2 rounded-lg text-white/80">
                                    {step.command}
                                </code>
                            </motion.div>
                        ))}
                    </div>
                </div>

                <motion.div
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    className="text-center px-4">
                    <h2 className="text-4xl font-bold text-white mb-6">
                        Ready to enhance your Discord server?
                    </h2>
                    <p className="text-white/60 text-xl mb-10">
                        Join thousands of servers already using Evict
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <a
                            href="/invite"
                            className="group px-8 py-3 bg-white text-black rounded-full font-medium hover:bg-opacity-90 
                 transition-all flex items-center justify-center gap-2">
                            <RiRobot2Line className="w-5 h-5" />
                            Add to Discord
                            <span className="inline-block transition-transform group-hover:translate-x-1">
                                →
                            </span>
                        </a>
                        <a
                            href="https://discord.gg/evict"
                            target="_blank"
                            className="group px-8 py-3 bg-[#5865F2] text-white rounded-full font-medium 
                 hover:bg-opacity-90 transition-all flex items-center justify-center gap-2">
                            <RiDiscordLine className="w-5 h-5" />
                            Join our Discord
                        </a>
                    </div>
                </motion.div>
            </div>
        </div>
    )
}
