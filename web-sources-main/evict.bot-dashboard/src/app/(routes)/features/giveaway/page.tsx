"use client"

import { motion } from "framer-motion"
import { Clock, Command, Crown, Gift, Sparkles, Star, Trophy, Users } from "lucide-react"

export default function GiveawayFeature() {
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
                            <span className="bg-clip-text text-transparent bg-gradient-to-r from-pink-400 to-purple-400">
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
                <motion.div
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    className="mb-20 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[
                        {
                            icon: <Trophy className="w-5 h-5 text-yellow-400" />,
                            title: "Multiple Winners",
                            description: "Support for multiple winners in a single giveaway"
                        },
                        {
                            icon: <Users className="w-5 h-5 text-blue-400" />,
                            title: "Role Requirements",
                            description: "Set specific role requirements for entry eligibility"
                        },
                        {
                            icon: <Star className="w-5 h-5 text-purple-400" />,
                            title: "Bonus Entries",
                            description: "Reward specific roles with bonus entries"
                        },
                        {
                            icon: <Clock className="w-5 h-5 text-green-400" />,
                            title: "Custom Duration",
                            description: "Set custom durations from minutes to weeks"
                        },
                        {
                            icon: <Crown className="w-5 h-5 text-pink-400" />,
                            title: "Server Boosters",
                            description: "Special perks for server boosters"
                        },
                        {
                            icon: <Sparkles className="w-5 h-5 text-orange-400" />,
                            title: "Auto-end",
                            description: "Automatic winner selection when time expires"
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
                                <Command className="w-6 h-6 text-pink-400" />
                                <h2 className="text-2xl md:text-3xl font-bold text-white">
                                    Command Examples
                                </h2>
                            </div>
                            <p className="text-white/60">
                                Start and manage giveaways with simple commands
                            </p>
                        </div>
                        <div className="p-6 space-y-4">
                            {[
                                {
                                    desc: "Start a basic giveaway",
                                    command:
                                        ";giveaway start #announcements Nitro --winners 1 --time 24h"
                                },
                                {
                                    desc: "Giveaway with bonus entries",
                                    command:
                                        ";giveaway start #giveaways Steam Game --winners 3 --bonus @Booster:2 @Nitro:1.5"
                                },
                                {
                                    desc: "Role-restricted giveaway",
                                    command:
                                        ";giveaway start #events Special Prize --require @Level10 --time 48h"
                                },
                                {
                                    desc: "Advanced configuration",
                                    command:
                                        ";giveaway start #special $100 Discord Nitro --winners 5 --time 72h --bonus @Booster:3 --require @Verified"
                                }
                            ].map((item, index) => (
                                <div key={index} className="bg-black/20 rounded-lg p-4">
                                    <div className="text-sm text-white/60 mb-2">{item.desc}</div>
                                    <div className="font-mono text-sm">
                                        <span className="text-white/80">{item.command}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <div className="flex items-center gap-3 mb-3">
                                <Gift className="w-6 h-6 text-pink-400" />
                                <h2 className="text-2xl font-bold text-white">Example Giveaways</h2>
                            </div>
                        </div>
                        <div className="p-6">
                            <div className="grid md:grid-cols-2 gap-6">
                                <div className="bg-black/20 rounded-lg p-6 border border-white/5">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="w-2 h-2 rounded-full bg-pink-500" />
                                        <span className="text-pink-400 font-semibold">
                                            GIVEAWAY
                                        </span>
                                    </div>

                                    <h4 className="text-xl font-semibold text-white mb-3">
                                        Nitro Giveaway! 🎉
                                    </h4>

                                    <div className="space-y-4">
                                        <div className="text-white/60 text-sm space-y-2">
                                            <p>React with 🎉 to enter!</p>
                                            <p>
                                                Ends in:{" "}
                                                <span className="text-white">24 hours</span>
                                            </p>
                                            <p>
                                                Winners: <span className="text-white">3</span>
                                            </p>
                                        </div>

                                        <div className="space-y-2">
                                            <div className="text-sm text-white/40">
                                                Bonus Entries:
                                            </div>
                                            <div className="flex items-center gap-2 text-sm bg-white/[0.02] rounded px-3 py-2">
                                                <div className="w-1.5 h-1.5 rounded-full bg-pink-400/60" />
                                                <span className="text-white/60">
                                                    Server Boosters (2x entries)
                                                </span>
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-between text-sm text-white/40">
                                            <span>Hosted by @evict</span>
                                            <span>89 entries</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-black/20 rounded-lg p-6 border border-white/5">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="w-2 h-2 rounded-full bg-purple-500" />
                                        <span className="text-purple-400 font-semibold">
                                            SPECIAL EVENT
                                        </span>
                                    </div>

                                    <h4 className="text-xl font-semibold text-white mb-3">
                                        🎮 $100 Steam Gift Card
                                    </h4>

                                    <div className="space-y-4">
                                        <div className="text-white/60 text-sm space-y-2">
                                            <p>React with 🎮 to enter!</p>
                                            <p>
                                                Ends in:{" "}
                                                <span className="text-white">72 hours</span>
                                            </p>
                                            <p>
                                                Winners: <span className="text-white">1</span>
                                            </p>
                                        </div>

                                        <div className="space-y-2">
                                            <div className="text-sm text-white/40">
                                                Requirements:
                                            </div>
                                            <div className="space-y-1">
                                                <div className="flex items-center gap-2 text-sm bg-white/[0.02] rounded px-3 py-2">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-purple-400/60" />
                                                    <span className="text-white/60">
                                                        Level 10+ Required
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-2 text-sm bg-white/[0.02] rounded px-3 py-2">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-purple-400/60" />
                                                    <span className="text-white/60">
                                                        Server Boosters (3x entries)
                                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-between text-sm text-white/40">
                                            <span>Hosted by @evict</span>
                                            <span>156 entries</span>
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
