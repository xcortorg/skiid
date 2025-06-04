"use client"

import { motion } from "framer-motion"
import { Command, MessageSquare, Palette, Settings, Variable, Wand2 } from "lucide-react"
import Link from "next/link"
import { IoTerminal } from "react-icons/io5"
import { RiExternalLinkLine } from "react-icons/ri"

export default function WelcomeFeature() {
    return (
        <div className="min-h-screen bg-gradient-to-b from-[#0A0A0B] to-black">
            <div className="relative border-b border-white/5">
                <div className="absolute inset-0 bg-[url('/noise.png')] opacity-5" />
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-24 pt-24 relative">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="text-center">
                        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 md:mb-6 mt-12">
                            <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                Welcome System
                            </span>
                        </h1>
                        <p className="text-base sm:text-lg text-gray-400 max-w-3xl mx-auto px-4">
                            Customize your server&apos;s welcome messages with powerful variables
                            and dynamic content
                        </p>
                    </motion.div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
                <div className="mb-16">
                    <motion.div
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="space-y-3">
                        <span className="text-4xl font-medium bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block mb-4">
                            Powerful customization
                        </span>
                        <p className="text-lg text-white/60 max-w-3xl">
                            Create engaging welcome messages that make new members feel at home. From simple text to rich embeds, the possibilities are endless.
                        </p>
                    </motion.div>
                </div>

                <motion.div
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    className="mb-20 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[
                        {
                            icon: Wand2,
                            title: "Custom Messages",
                            description:
                                "Create personalized welcome messages with variables and custom formatting"
                        },
                        {
                            icon: MessageSquare,
                            title: "Multiple Channels",
                            description:
                                "Send welcome messages to different channels based on roles or conditions"
                        },
                        {
                            icon: Palette,
                            title: "Embed Builder",
                            description:
                                "Design beautiful embeds with our visual editor or JSON configuration"
                        }
                    ].map((feature, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-50px" }}
                            transition={{ duration: 0.5, delay: index * 0.1 }}
                            className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl 
                                     hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] 
                                     shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)] p-6">
                            <div className="relative z-10">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="p-2.5 rounded-lg bg-white/5 border border-evict-primary/20">
                                        <feature.icon className="w-5 h-5 text-evict-primary/80" />
                                    </div>
                                    <h3 className="text-lg font-medium text-evict-primary/90">{feature.title}</h3>
                                </div>
                                <p className="text-white/60 text-sm">{feature.description}</p>
                            </div>
                            <div className="absolute inset-0 bg-gradient-to-br from-evict-primary/5 to-transparent 
                                          opacity-0 group-hover:opacity-25 transition-opacity duration-500 rounded-3xl" />
                        </motion.div>
                    ))}
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl border border-white/[0.05] overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-white/5 border border-evict-primary/20">
                                    <Variable className="w-5 h-5 text-evict-primary/80" />
                                </div>
                                <h2 className="text-2xl font-medium text-white">Dynamic Variables</h2>
                            </div>
                            <p className="text-white/60">
                                Personalize your welcome messages with these powerful variables. Use
                                them in any combination to create unique greetings.
                            </p>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                <div>
                                    <h3 className="text-lg font-medium text-evict-primary/90 mb-4">
                                        User Variables
                                    </h3>
                                    <div className="space-y-3">
                                        {[
                                            {
                                                variable: "{user}",
                                                desc: "Full username with discriminator",
                                                example: "66adam#0"
                                            },
                                            {
                                                variable: "{user.name}",
                                                desc: "Username only",
                                                example: "66adam"
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
                                                example: "@66adam"
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
                                            <div key={index} className="group bg-black/20 rounded-lg p-3 hover:bg-black/30 transition-colors border border-white/5">
                                                <code className="text-sm font-mono text-evict-primary/80">
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
                                    <h3 className="text-lg font-medium text-evict-primary/90 mb-4">
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
                                            <div key={index} className="group bg-black/20 rounded-lg p-3 hover:bg-black/30 transition-colors border border-white/5">
                                                <code className="text-sm font-mono text-evict-primary/80">
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
                        <div className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl border border-white/[0.05] overflow-hidden hover:bg-white/[0.04] transition-all duration-300">
                            <div className="border-b border-white/5 p-6">
                                <div className="flex items-center gap-3">
                                    <div className="p-2.5 rounded-lg bg-white/5 border border-evict-primary/20">
                                        <Settings className="w-5 h-5 text-evict-primary/80" />
                                    </div>
                                    <h3 className="text-xl font-medium text-evict-primary/90">
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
                                    <button className="px-6 py-3 bg-evict-primary text-evict-100 rounded-xl font-medium hover:bg-opacity-90 transition-all flex items-center justify-center gap-2">
                                        Open Dashboard
                                        <RiExternalLinkLine className="w-4 h-4" />
                                    </button>
                                </Link>
                            </div>
                        </div>

                        <div className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl border border-white/[0.05] overflow-hidden hover:bg-white/[0.04] transition-all duration-300">
                            <div className="border-b border-white/5 p-6">
                                <div className="flex items-center gap-3">
                                    <div className="p-2.5 rounded-lg bg-white/5 border border-evict-primary/20">
                                        <Command className="w-5 h-5 text-evict-primary/80" />
                                    </div>
                                    <h3 className="text-xl font-medium text-evict-primary/90">Command Setup</h3>
                                </div>
                            </div>
                            <div className="p-6">
                                <p className="text-white/60 mb-4">
                                    Set up welcome messages directly through Discord using simple
                                    commands.
                                </p>
                                <div className="bg-black/20 rounded-lg p-3 font-mono text-sm text-white/80 group-hover:bg-black/30 transition-colors border border-white/5">
                                    ;welcome add #welcome Welcome {"{user.mention}"} to the server!
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl border border-white/[0.05] overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-white/5 border border-evict-primary/20">
                                    <MessageSquare className="w-5 h-5 text-evict-primary/80" />
                                </div>
                                <h2 className="text-2xl font-medium text-white">Example Messages</h2>
                            </div>
                            <p className="text-white/60">
                                Get inspired by these example welcome messages
                            </p>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="bg-black/20 rounded-lg p-4 border border-evict-primary/20">
                                    <div className="flex items-start gap-4">
                                        <img
                                            src="/avs/adam-dc.png"
                                            alt="User Avatar"
                                            className="w-16 h-16 rounded-full"
                                        />
                                        <div>
                                            <div className="font-medium text-white mb-2">
                                                Welcome 66adam!
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

                                <div className="bg-black/20 rounded-lg p-4 border border-evict-primary/20">
                                    <div className="text-center">
                                        <img
                                            src="/avs/adam-dc.png"
                                            alt="User Avatar"
                                            className="w-20 h-20 rounded-full mx-auto mb-4 ring-4 ring-evict-primary/20"
                                        />
                                        <h3 className="text-xl font-bold text-white mb-2">
                                            Welcome to the server!
                                        </h3>
                                        <p className="text-white/80 mb-4">
                                            Hey <span className="text-evict-primary">@66adam</span>!
                                            Thanks for joining. You&apos;re our 1,234th member!
                                        </p>
                                        <div className="flex justify-center gap-2 text-sm">
                                            <span className="px-3 py-1 bg-evict-primary/20 rounded-full text-evict-primary">
                                                Member #1234
                                            </span>
                                            <span className="px-3 py-1 bg-evict-primary/20 rounded-full text-evict-primary">
                                                New Member
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    key="server-cta"
                    initial={{ opacity: 0, x: 20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true, margin: "-100px" }}
                    transition={{ duration: 0.4 }}
                    className="relative lg:pl-12 text-center lg:text-left">
                    <div className="absolute inset-0 rounded-3xl bg-gradient-to-r from-evict-primary/10 via-transparent to-evict-primary/10 opacity-20 blur-3xl -z-10" />
                    <div className="relative">
                        <span className="text-4xl font-bold bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent mb-4 block">
                            Ready to welcome new members?
                        </span>
                        <div className="flex flex-col lg:flex-row items-center gap-8 mt-8">
                            <div className="flex-1 space-y-4">
                                <p className="text-white/60 text-xl">
                                    Join thousands of servers using Evict&apos;s welcome system
                                </p>
                                <div className="flex flex-wrap gap-6 justify-center lg:justify-start text-white/40">
                                    <div className="flex items-center gap-2">
                                        <Wand2 className="w-5 h-5 text-evict-primary" />
                                        Custom messages
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Variable className="w-5 h-5 text-evict-primary" />
                                        Dynamic variables
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Palette className="w-5 h-5 text-evict-primary" />
                                        Rich embeds
                                    </div>
                                </div>
                            </div>
                            <div className="flex flex-col sm:flex-row gap-3">
                                <motion.div
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    viewport={{ once: true }}
                                    transition={{ duration: 0.2 }}>
                                    <Link
                                        href="/invite"
                                        className="px-6 py-3 bg-evict-primary text-evict-100 rounded-xl font-medium hover:bg-opacity-90 transition-all flex items-center justify-center gap-2 min-w-[160px]">
                                        Add to Discord
                                        <RiExternalLinkLine className="w-4 h-4" />
                                    </Link>
                                </motion.div>
                                <motion.div
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    viewport={{ once: true }}
                                    transition={{ duration: 0.2 }}>
                                    <Link
                                        href="/commands"
                                        className="px-6 py-3 bg-evict-200/50 text-evict-primary rounded-xl font-medium hover:bg-evict-200/70 transition-all border border-evict-primary/20 flex items-center justify-center gap-2 min-w-[160px]">
                                        <IoTerminal className="w-4 h-4" />
                                        View Commands
                                    </Link>
                                </motion.div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    )
}
