"use client"

import { motion } from "framer-motion"
import { Clock, Command, Crown, Gift, Sparkles, Star, Trophy, Users } from "lucide-react"
import Link from "next/link"
import { IoTerminal } from "react-icons/io5"
import { RiExternalLinkLine } from "react-icons/ri"

export default function GiveawayFeature() {
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
                                Giveaway System
                            </span>
                        </h1>
                        <p className="text-base sm:text-lg text-gray-400 max-w-3xl mx-auto px-4">
                            Create engaging giveaways with custom requirements, multiple winners,
                            and bonus entries
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
                            Feature-rich giveaway system
                        </span>
                        <p className="text-lg text-white/60 max-w-3xl">
                            From simple drops to complex events, our giveaway system provides all the tools you need to engage your community.
                        </p>
                    </motion.div>
                </div>

                <motion.div
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    className="mb-20 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[
                        {
                            icon: Trophy,
                            title: "Multiple Winners",
                            description: "Support for multiple winners in a single giveaway"
                        },
                        {
                            icon: Users,
                            title: "Role Requirements",
                            description: "Set specific role requirements for entry eligibility"
                        },
                        {
                            icon: Star,
                            title: "Bonus Entries",
                            description: "Reward specific roles with bonus entries"
                        },
                        {
                            icon: Clock,
                            title: "Custom Duration",
                            description: "Set custom durations from minutes to weeks"
                        },
                        {
                            icon: Crown,
                            title: "Server Boosters",
                            description: "Special perks for server boosters"
                        },
                        {
                            icon: Sparkles,
                            title: "Auto-end",
                            description: "Automatic winner selection when time expires"
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
                    <div className="relative">
                        <div className="absolute inset-0 bg-gradient-to-r from-evict-primary/5 to-transparent opacity-30 blur-3xl rounded-full" />

                        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5 }}
                                className="lg:col-span-2 group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-6 
                                     hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="p-3 rounded-xl bg-white/5 border border-evict-primary/20">
                                        <Gift className="w-6 h-6 text-evict-primary/80" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-evict-primary/90">
                                        Active Giveaway
                                    </h3>
                                </div>

                                <div className="bg-black/20 rounded-xl p-6 border border-white/5">
                                    <div className="flex items-center justify-between mb-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-2 h-2 rounded-full bg-evict-primary/80 animate-pulse" />
                                            <span className="text-evict-primary/80 font-medium text-sm">
                                                LIVE NOW
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs px-3 py-1 bg-black/30 rounded-full text-white/40">
                                            <Clock className="w-3 h-3" />
                                            <span>23:45:12</span>
                                        </div>
                                    </div>

                                    <div className="flex flex-col md:flex-row gap-6">
                                        <div className="flex-1">
                                            <h4 className="text-xl font-semibold text-white/90 mb-2">
                                                🎮 $100 Steam Gift Card
                                            </h4>
                                            <p className="text-white/60 text-sm mb-4">
                                                React with 🎮 to enter! One lucky winner will be
                                                randomly selected when the giveaway ends.
                                            </p>

                                            <div className="grid grid-cols-2 gap-3 mb-4">
                                                <div className="bg-white/[0.02] rounded-lg p-3 border border-white/5">
                                                    <div className="text-xs text-white/40 mb-1">
                                                        Winners
                                                    </div>
                                                    <div className="text-lg font-medium text-white/90">
                                                        1
                                                    </div>
                                                </div>
                                                <div className="bg-white/[0.02] rounded-lg p-3 border border-white/5">
                                                    <div className="text-xs text-white/40 mb-1">
                                                        Entries
                                                    </div>
                                                    <div className="text-lg font-medium text-white/90">
                                                        156
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2 text-sm text-white/40">
                                                <span>Hosted by</span>
                                                <span className="text-white/80">@evict</span>
                                            </div>
                                        </div>

                                        <div className="md:w-40 flex-shrink-0 flex flex-col items-center justify-center">
                                            <div className="w-32 h-32 rounded-full bg-gradient-to-br from-evict-primary/20 to-transparent flex items-center justify-center mb-3">
                                                <div className="w-24 h-24 rounded-full bg-black/30 flex items-center justify-center">
                                                    <Gift className="w-10 h-10 text-evict-primary/60" />
                                                </div>
                                            </div>
                                            <div className="text-center">
                                                <div className="text-xs text-white/40 mb-1">
                                                    Time Remaining
                                                </div>
                                                <div className="text-lg font-medium text-white/90">
                                                    23:45:12
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>

                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5, delay: 0.1 }}
                                className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-6 
                                     hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]">
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="p-3 rounded-xl bg-white/5 border border-evict-primary/20">
                                        <Command className="w-6 h-6 text-evict-primary/80" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-evict-primary/90">
                                        Quick Commands
                                    </h3>
                                </div>

                                <div className="space-y-3">
                                    <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:bg-black/30 transition-colors cursor-pointer group">
                                        <div className="flex items-center justify-between">
                                            <span className="text-white/80 text-sm group-hover:text-white/90 transition-colors">
                                                Basic Giveaway
                                            </span>
                                            <span className="text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                /giveaway start
                                            </span>
                                        </div>
                                        <div className="mt-1 text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                            Start a simple giveaway with default settings
                                        </div>
                                    </div>

                                    <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:bg-black/30 transition-colors cursor-pointer group">
                                        <div className="flex items-center justify-between">
                                            <span className="text-white/80 text-sm group-hover:text-white/90 transition-colors">
                                                Multiple Winners
                                            </span>
                                            <span className="text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                --winners 3
                                            </span>
                                        </div>
                                        <div className="mt-1 text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                            Select multiple winners for your giveaway
                                        </div>
                                    </div>

                                    <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:bg-black/30 transition-colors cursor-pointer group">
                                        <div className="flex items-center justify-between">
                                            <span className="text-white/80 text-sm group-hover:text-white/90 transition-colors">
                                                Role Requirements
                                            </span>
                                            <span className="text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                --require @Role
                                            </span>
                                        </div>
                                        <div className="mt-1 text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                            Restrict entry to users with specific roles
                                        </div>
                                    </div>

                                    <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:bg-black/30 transition-colors cursor-pointer group">
                                        <div className="flex items-center justify-between">
                                            <span className="text-white/80 text-sm group-hover:text-white/90 transition-colors">
                                                Bonus Entries
                                            </span>
                                            <span className="text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                                --bonus @Role:2
                                            </span>
                                        </div>
                                        <div className="mt-1 text-xs text-white/40 group-hover:text-white/60 transition-colors">
                                            Give specific roles bonus entries
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
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
                            Start Your First Giveaway
                        </span>
                        <div className="flex flex-col lg:flex-row items-center gap-8 mt-8">
                            <div className="flex-1 space-y-4">
                                <p className="text-white/60 text-xl">
                                    Join thousands of servers using Evict&apos;s giveaway system
                                </p>
                                <div className="flex flex-wrap gap-6 justify-center lg:justify-start text-white/40">
                                    <div className="flex items-center gap-2">
                                        <Trophy className="w-5 h-5 text-evict-primary" />
                                        Multiple winners
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Star className="w-5 h-5 text-evict-primary" />
                                        Bonus entries
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Gift className="w-5 h-5 text-evict-primary" />
                                        Custom requirements
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
