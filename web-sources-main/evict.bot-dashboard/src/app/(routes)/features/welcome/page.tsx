"use client"

import { motion } from "framer-motion"
import { Command, MessageSquare, Palette, Settings, Variable, Wand2 } from "lucide-react"
import Link from "next/link"

export default function WelcomeFeature() {
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
                                Welcome System
                            </span>
                        </h1>
                        <p className="text-base sm:text-lg text-gray-400 max-w-3xl mx-auto px-4">
                            Customize your server&apos;s welcome messages with powerful variables and
                            dynamic content
                        </p>
                    </motion.div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
                <motion.div
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    className="mb-20 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[
                        {
                            icon: <Wand2 className="w-5 h-5 text-purple-400" />,
                            title: "Custom Messages",
                            description:
                                "Create personalized welcome messages with variables and custom formatting"
                        },
                        {
                            icon: <MessageSquare className="w-5 h-5 text-blue-400" />,
                            title: "Multiple Channels",
                            description:
                                "Send welcome messages to different channels based on roles or conditions"
                        },
                        {
                            icon: <Palette className="w-5 h-5 text-green-400" />,
                            title: "Embed Builder",
                            description:
                                "Design beautiful embeds with our visual editor or JSON configuration"
                        }
                    ].map((feature, index) => (
                        <div
                            key={index}
                            className="bg-[#0A0A0B] border border-white/5 rounded-xl p-6">
                            <div className="flex items-center gap-3 mb-4">
                                {feature.icon}
                                <h3 className="text-lg font-bold text-white">{feature.title}</h3>
                            </div>
                            <p className="text-white/60">{feature.description}</p>
                        </div>
                    ))}
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <div className="flex items-center gap-3 mb-3">
                                <Variable className="w-6 h-6 text-blue-400" />
                                <h2 className="text-2xl md:text-3xl font-bold text-white">
                                    Dynamic Variables
                                </h2>
                            </div>
                            <p className="text-white/60">
                                Personalize your welcome messages with these powerful variables. Use
                                them in any combination to create unique greetings.
                            </p>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-4">
                                        User Variables
                                    </h3>
                                    <div className="space-y-3">
                                        {[
                                            {
                                                variable: "{user}",
                                                desc: "Full username with discriminator",
                                                example: "x14c#0"
                                            },
                                            {
                                                variable: "{user.name}",
                                                desc: "Username only",
                                                example: "x14c"
                                            },
                                            {
                                                variable: "{user.discriminator}",
                                                desc: "User's discriminator",
                                                example: "#0"
                                            },
                                            {
                                                variable: "{user.id}",
                                                desc: "User's unique ID",
                                                example: "123456789012345678"
                                            },
                                            {
                                                variable: "{user.mention}",
                                                desc: "Mentions the user",
                                                example: "@x14c"
                                            },
                                            {
                                                variable: "{user.avatar}",
                                                desc: "User's avatar URL",
                                                example: "https://..."
                                            },
                                            {
                                                variable: "{user.created_at}",
                                                desc: "Account creation date",
                                                example: "2020-05-01"
                                            },
                                            {
                                                variable: "{user.joined_at}",
                                                desc: "Server join date",
                                                example: "2021-06-15"
                                            }
                                        ].map((item, index) => (
                                            <div key={index} className="bg-black/20 rounded-lg p-3">
                                                <code className="text-sm font-mono text-blue-400">
                                                    {item.variable}
                                                </code>
                                                <p className="text-sm text-white/80 mt-1">
                                                    {item.desc}
                                                </p>
                                                <p className="text-xs text-white/40 font-mono mt-1">
                                                    Example: {item.example}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-4">
                                        Server Variables
                                    </h3>
                                    <div className="space-y-3">
                                        {[
                                            {
                                                variable: "{server.name}",
                                                desc: "Server name",
                                                example: "Evict Community"
                                            },
                                            {
                                                variable: "{server.id}",
                                                desc: "Server's unique ID",
                                                example: "987654321098765432"
                                            },
                                            {
                                                variable: "{server.member_count}",
                                                desc: "Total member count",
                                                example: "1,234"
                                            },
                                            {
                                                variable: "{server.boost_level}",
                                                desc: "Server boost level",
                                                example: "Level 2"
                                            },
                                            {
                                                variable: "{server.boost_count}",
                                                desc: "Number of boosts",
                                                example: "15"
                                            },
                                            {
                                                variable: "{server.created_at}",
                                                desc: "Server creation date",
                                                example: "2019-01-15"
                                            },
                                            {
                                                variable: "{server.icon}",
                                                desc: "Server icon URL",
                                                example: "https://..."
                                            },
                                            {
                                                variable: "{server.owner}",
                                                desc: "Server owner's name",
                                                example: "OwnerName#0"
                                            }
                                        ].map((item, index) => (
                                            <div key={index} className="bg-black/20 rounded-lg p-3">
                                                <code className="text-sm font-mono text-green-400">
                                                    {item.variable}
                                                </code>
                                                <p className="text-sm text-white/80 mt-1">
                                                    {item.desc}
                                                </p>
                                                <p className="text-xs text-white/40 font-mono mt-1">
                                                    Example: {item.example}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                            <div className="border-b border-white/5 p-6">
                                <div className="flex items-center gap-3">
                                    <Settings className="w-5 h-5 text-blue-400" />
                                    <h3 className="text-xl font-bold text-white">
                                        Dashboard Setup
                                    </h3>
                                </div>
                            </div>
                            <div className="p-6">
                                <p className="text-white/60 mb-4">
                                    Configure your welcome messages easily through our intuitive
                                    dashboard interface.
                                </p>
                                <Link href="/dashboard">
                                    <button className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors">
                                        Open Dashboard
                                    </button>
                                </Link>
                            </div>
                        </div>

                        <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                            <div className="border-b border-white/5 p-6">
                                <div className="flex items-center gap-3">
                                    <Command className="w-5 h-5 text-purple-400" />
                                    <h3 className="text-xl font-bold text-white">Command Setup</h3>
                                </div>
                            </div>
                            <div className="p-6">
                                <p className="text-white/60 mb-4">
                                    Set up welcome messages directly through Discord using simple
                                    commands.
                                </p>
                                <div className="bg-black/20 rounded-lg p-3 font-mono text-sm text-white/80">
                                    ;welcome add #welcome Welcome {"{user.mention}"} to the server!
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <h2 className="text-2xl font-bold text-white mb-3">
                                Example Welcome Messages
                            </h2>
                            <p className="text-white/60">
                                Get inspired by these example welcome messages
                            </p>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="bg-[#18191c] rounded-lg p-4 border-l-4 border-blue-500">
                                    <div className="flex items-start gap-4">
                                        <img
                                            src="https://r2.evict.bot/ba4326aff26bae608592599e14db1239.png"
                                            alt="User Avatar"
                                            className="w-16 h-16 rounded-full"
                                        />
                                        <div>
                                            <div className="font-medium text-white mb-2">
                                                Welcome x14c!
                                            </div>
                                            <p className="text-white/80">
                                                You are member #1234. Enjoy your stay!
                                            </p>
                                            <div className="text-xs text-white/40 mt-2">
                                                Account created: 2020-05-01
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-[#18191c] rounded-lg p-4">
                                    <div className="text-center">
                                        <img
                                            src="https://r2.evict.bot/ba4326aff26bae608592599e14db1239.png"
                                            alt="User Avatar"
                                            className="w-20 h-20 rounded-full mx-auto mb-4 ring-4 ring-blue-500/20"
                                        />
                                        <h3 className="text-xl font-bold text-white mb-2">
                                            Welcome to the server!
                                        </h3>
                                        <p className="text-white/80 mb-4">
                                            Hey <span className="text-blue-400">@x14c</span>!
                                            Thanks for joining. You&apos;re our 1,234th member!
                                        </p>
                                        <div className="flex justify-center gap-2 text-sm">
                                            <span className="px-3 py-1 bg-blue-500/20 rounded-full text-blue-400">
                                                Member #1234
                                            </span>
                                            <span className="px-3 py-1 bg-purple-500/20 rounded-full text-purple-400">
                                                New Member
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    )
}
