"use client"

import { motion } from "framer-motion"
import { Briefcase, Building2, Dog, Gamepad2, PiggyBank, ShoppingBag, Trophy } from "lucide-react"

export default function EconomyFeature() {
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
                                Economy System
                            </span>
                        </h1>
                        <p className="text-base sm:text-lg text-gray-400 max-w-3xl mx-auto px-4">
                            A complete economy system with businesses, gambling, pets, and more
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
                            icon: <PiggyBank className="w-5 h-5 text-green-400" />,
                            title: "Banking System",
                            description: "Earn interest, manage deposits, and upgrade capacity"
                        },
                        {
                            icon: <Building2 className="w-5 h-5 text-blue-400" />,
                            title: "Business Management",
                            description: "Create and manage your own business empire"
                        },
                        {
                            icon: <ShoppingBag className="w-5 h-5 text-purple-400" />,
                            title: "Item Shop",
                            description: "Buy, sell, and trade items and roles"
                        },
                        {
                            icon: <Gamepad2 className="w-5 h-5 text-pink-400" />,
                            title: "Gambling Games",
                            description: "12+ unique gambling games with different odds"
                        },
                        {
                            icon: <Dog className="w-5 h-5 text-yellow-400" />,
                            title: "Pet System",
                            description: "Adopt, breed, and adventure with pets"
                        },
                        {
                            icon: <Trophy className="w-5 h-5 text-orange-400" />,
                            title: "Competitions",
                            description: "Join tournaments and climb leaderboards"
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
                                <Briefcase className="w-6 h-6 text-blue-400" />
                                <h2 className="text-2xl font-bold text-white">Business System</h2>
                            </div>
                            <p className="text-white/60">
                                Create and manage your own business with employees and job listings
                            </p>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-4">
                                    <div className="bg-black/20 rounded-lg p-4">
                                        <h4 className="text-white font-medium mb-2">Quick Start</h4>
                                        <div className="space-y-2 font-mono text-sm">
                                            <div className="text-white/80">
                                                ;business create My Shop
                                            </div>
                                            <div className="text-white/80">
                                                ;business hire @user 1000 Manager
                                            </div>
                                            <div className="text-white/80">
                                                ;business deposit 5000
                                            </div>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        {[
                                            "Hire employees",
                                            "Post job listings",
                                            "Manage payroll",
                                            "Track performance",
                                            "Upgrade capacity",
                                            "Compete with others"
                                        ].map((item, i) => (
                                            <div
                                                key={i}
                                                className="flex items-center gap-2 text-sm bg-white/[0.02] rounded-lg px-3 py-2">
                                                <div className="w-1.5 h-1.5 rounded-full bg-blue-400/60" />
                                                <span className="text-white/60">{item}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="bg-black/20 rounded-lg p-6 border border-white/5">
                                    <div className="flex items-center gap-3 mb-4">
                                        <Building2 className="w-5 h-5 text-blue-400" />
                                        <h3 className="text-lg font-bold text-white">Business</h3>
                                    </div>
                                    <div className="space-y-4">
                                        <div className="grid grid-cols-2 gap-3">
                                            <div className="bg-white/[0.02] rounded-lg p-3">
                                                <div className="text-sm text-white/40 mb-1">
                                                    Balance
                                                </div>
                                                <div className="text-white font-medium">
                                                    50,000 coins
                                                </div>
                                            </div>
                                            <div className="bg-white/[0.02] rounded-lg p-3">
                                                <div className="text-sm text-white/40 mb-1">
                                                    Employees
                                                </div>
                                                <div className="text-white font-medium">5/10</div>
                                            </div>
                                        </div>
                                        <div className="bg-white/[0.02] rounded-lg p-3">
                                            <div className="text-sm text-white/40 mb-2">
                                                Active Jobs
                                            </div>
                                            <div className="space-y-2">
                                                <div className="flex justify-between text-sm">
                                                    <span className="text-white/60">
                                                        Store Manager
                                                    </span>
                                                    <span className="text-white">2,000/week</span>
                                                </div>
                                                <div className="flex justify-between text-sm">
                                                    <span className="text-white/60">
                                                        Sales Associate
                                                    </span>
                                                    <span className="text-white">1,000/week</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="mb-20">
                    <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <div className="flex items-center gap-3 mb-3">
                                <Gamepad2 className="w-6 h-6 text-pink-400" />
                                <h2 className="text-2xl font-bold text-white">Gambling Games</h2>
                            </div>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                {[
                                    {
                                        name: "Blackjack",
                                        cmd: ";gamble blackjack",
                                        odds: "99.5% RTP"
                                    },
                                    { name: "Slots", cmd: ";gamble slots", odds: "96% RTP" },
                                    { name: "Crash", cmd: ";gamble crash", odds: "97% RTP" },
                                    {
                                        name: "Roulette",
                                        cmd: ";gamble roulette",
                                        odds: "97.3% RTP"
                                    },
                                    { name: "Mines", cmd: ";gamble mines", odds: "96-98% RTP" },
                                    { name: "Poker Dice", cmd: ";gamble poker", odds: "97.5% RTP" }
                                ].map((game, i) => (
                                    <div key={i} className="bg-black/20 rounded-lg p-4">
                                        <h4 className="text-white font-medium mb-2">{game.name}</h4>
                                        <div className="text-sm text-white/60 mb-2">
                                            {game.odds}
                                        </div>
                                        <div className="font-mono text-sm text-white/80">
                                            {game.cmd}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }}>
                    <div className="bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <div className="flex items-center gap-3 mb-3">
                                <Dog className="w-6 h-6 text-yellow-400" />
                                <h2 className="text-2xl font-bold text-white">Pet System</h2>
                            </div>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-4">
                                    <div className="bg-black/20 rounded-lg p-4">
                                        <h4 className="text-white font-medium mb-2">
                                            Pet Commands
                                        </h4>
                                        <div className="space-y-2 font-mono text-sm">
                                            <div className="text-white/80">
                                                ;pet adopt dog Buddy
                                            </div>
                                            <div className="text-white/80">;pet feed Buddy</div>
                                            <div className="text-white/80">;pet play Buddy</div>
                                            <div className="text-white/80">
                                                ;pet adventure Buddy
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-black/20 rounded-lg p-6 border border-white/5">
                                    <h4 className="text-lg font-bold text-white mb-4">
                                        Pet Features
                                    </h4>
                                    <div className="space-y-3">
                                        {[
                                            "Multiple pet types",
                                            "Breeding system",
                                            "Adventure rewards",
                                            "Pet collections",
                                            "Skill training",
                                            "Pet trading"
                                        ].map((feature, i) => (
                                            <div
                                                key={i}
                                                className="flex items-center gap-2 text-sm bg-white/[0.02] rounded-lg px-3 py-2">
                                                <div className="w-1.5 h-1.5 rounded-full bg-yellow-400/60" />
                                                <span className="text-white/60">{feature}</span>
                                            </div>
                                        ))}
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
