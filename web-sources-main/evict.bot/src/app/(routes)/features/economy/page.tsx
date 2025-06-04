"use client"

import { AnimatePresence, motion } from "framer-motion"
import {
    Award,
    BarChart,
    Briefcase,
    Building2,
    Dog,
    Gamepad2,
    Gift,
    History,
    PiggyBank,
    ShoppingBag,
    Star,
    Trophy,
    Users
} from "lucide-react"
import Link from "next/link"
import CountUp from "react-countup"
import { IoTerminal } from "react-icons/io5"
import { RiExternalLinkLine } from "react-icons/ri"
import { useInView } from "react-intersection-observer"

function Counter({ from, to }: { from: number; to: number }) {
    const { ref, inView } = useInView({
        threshold: 0.2,
        triggerOnce: true
    })

    return (
        <span ref={ref} className="inline-block">
            {inView ? (
                <CountUp
                    start={from}
                    end={to}
                    separator=","
                    duration={2}
                    className="text-white font-semibold"
                />
            ) : (
                from.toLocaleString()
            )}
        </span>
    )
}

const container = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.08,
            delayChildren: 0.1,
            type: "spring",
            stiffness: 50,
            damping: 20
        }
    }
}

const item = {
    hidden: {
        opacity: 0,
        y: 8
    },
    show: {
        opacity: 1,
        y: 0,
        transition: {
            type: "spring",
            stiffness: 100,
            damping: 20,
            duration: 0.3
        }
    }
}

export default function EconomyFeature() {
    return (
        <AnimatePresence mode="wait">
            <motion.div
                key="economy"
                className="relative w-full overflow-x-hidden mt-16"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}>
                <motion.div
                    className="fixed inset-0 z-0 pointer-events-none opacity-[0.015] bg-noise"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0.015 }}
                    transition={{ duration: 0.3 }}
                />
                <motion.div
                    className="fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-white/5 via-transparent to-zinc-400/5 mix-blend-overlay"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3 }}
                />

                <div className="relative min-h-[calc(100vh-4rem)]">
                    <motion.div
                        variants={container}
                        initial="hidden"
                        animate="show"
                        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
                        <motion.div variants={item} className="text-center mb-12">
                            <motion.h1
                                variants={item}
                                className="text-4xl sm:text-5xl md:text-7xl font-bold mb-4">
                                <span className="block bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                    Economy System
                                </span>
                            </motion.h1>
                            <motion.p
                                variants={item}
                                className="text-lg md:text-xl text-transparent bg-clip-text bg-gradient-to-r from-white to-evict-primary max-w-3xl mx-auto">
                                A complete economy system with businesses, gambling, pets, and more
                            </motion.p>
                        </motion.div>

                        <motion.div variants={item} className="mb-12">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {[
                                    {
                                        icon: <Users className="w-5 h-5 text-evict-primary" />,
                                        label: "Active Users",
                                        value: <Counter from={0} to={15000} />
                                    },
                                    {
                                        icon: <Building2 className="w-5 h-5 text-evict-primary" />,
                                        label: "Businesses",
                                        value: <Counter from={0} to={2000} />
                                    },
                                    {
                                        icon: <PiggyBank className="w-5 h-5 text-evict-primary" />,
                                        label: "Total Economy",
                                        value: "150M+"
                                    },
                                    {
                                        icon: <Dog className="w-5 h-5 text-evict-primary" />,
                                        label: "Active Pets",
                                        value: <Counter from={0} to={400} />
                                    }
                                ].map((stat, i) => (
                                    <div
                                        key={i}
                                        className="group relative bg-gradient-to-br from-white/[0.03] to-transparent border border-white/5 rounded-xl p-4 hover:border-evict-primary/20 transition-colors duration-300">
                                        <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-evict-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                        <div className="relative flex flex-col items-center text-center">
                                            {stat.icon}
                                            <div className="mt-2 text-2xl font-bold text-evict-primary">
                                                {stat.value}
                                            </div>
                                            <div className="text-sm text-white/40">
                                                {stat.label}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </motion.div>

                        <motion.div
                            variants={container}
                            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
                            {[
                                {
                                    icon: <PiggyBank className="w-5 h-5 text-evict-primary" />,
                                    title: "Banking System",
                                    description:
                                        "Earn interest, manage deposits, and upgrade capacity",
                                    stat: "50M+",
                                    statLabel: "Total Coins Saved"
                                },
                                {
                                    icon: <Building2 className="w-5 h-5 text-evict-primary" />,
                                    title: "Business Management",
                                    description: "Create and manage your own business empire",
                                    stat: "10K+",
                                    statLabel: "Active Businesses"
                                },
                                {
                                    icon: <ShoppingBag className="w-5 h-5 text-evict-primary" />,
                                    title: "Item Shop",
                                    description: "Buy, sell, and trade items and roles",
                                    stat: "100+",
                                    statLabel: "Unique Items"
                                }
                            ].map((feature, index) => (
                                <motion.div
                                    key={index}
                                    variants={item}
                                    className="group relative bg-gradient-to-br from-white/[0.03] to-transparent border border-white/5 rounded-xl p-6 hover:border-evict-primary/20 transition-colors duration-300">
                                    <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-evict-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                    <div className="relative">
                                        <div className="flex items-center gap-3 mb-4">
                                            {feature.icon}
                                            <h3 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                                {feature.title}
                                            </h3>
                                        </div>
                                        <p className="text-white/60 mb-4">{feature.description}</p>
                                        <div className="flex items-baseline gap-1">
                                            <span className="text-2xl font-bold text-evict-primary">
                                                {feature.stat}
                                            </span>
                                            <span className="text-sm text-white/40">
                                                {feature.statLabel}
                                            </span>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </motion.div>

                        <motion.div
                            variants={container}
                            className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
                            <motion.div
                                variants={item}
                                className="group relative bg-gradient-to-br from-white/[0.03] to-transparent border border-white/5 rounded-xl overflow-hidden">
                                <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-evict-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                <div className="border-b border-white/5 p-6 relative">
                                    <div className="flex items-center gap-3">
                                        <Gamepad2 className="w-6 h-6 text-evict-primary" />
                                        <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                            Gambling Games
                                        </h2>
                                    </div>
                                </div>
                                <div className="p-6 relative">
                                    <div className="grid grid-cols-2 gap-4">
                                        {[
                                            {
                                                name: "Blackjack",
                                                cmd: ";gamble blackjack",
                                                odds: "99.5% RTP",
                                                popular: true
                                            },
                                            {
                                                name: "Slots",
                                                cmd: ";gamble slots",
                                                odds: "96% RTP"
                                            },
                                            {
                                                name: "Crash",
                                                cmd: ";gamble crash",
                                                odds: "97% RTP",
                                                popular: true
                                            },
                                            {
                                                name: "Roulette",
                                                cmd: ";gamble roulette",
                                                odds: "97.3% RTP"
                                            }
                                        ].map((game, i) => (
                                            <div
                                                key={i}
                                                className="group/game relative bg-black/20 rounded-lg p-4 border border-white/5 hover:border-evict-primary/20 transition-colors duration-300">
                                                <div className="flex items-center justify-between mb-2">
                                                    <h4 className="text-white font-medium">
                                                        {game.name}
                                                    </h4>
                                                    {game.popular && (
                                                        <span className="text-[10px] font-medium bg-evict-primary/10 text-evict-primary px-2 py-0.5 rounded-full">
                                                            POPULAR
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="text-sm text-evict-primary mb-2">
                                                    {game.odds}
                                                </div>
                                                <div className="font-mono text-sm text-white/80 group-hover/game:text-evict-primary/80 transition-colors duration-300">
                                                    {game.cmd}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>

                            <motion.div
                                variants={item}
                                className="group relative bg-gradient-to-br from-white/[0.03] to-transparent border border-white/5 rounded-xl overflow-hidden">
                                <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-evict-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                <div className="border-b border-white/5 p-6 relative">
                                    <div className="flex items-center gap-3">
                                        <Dog className="w-6 h-6 text-evict-primary" />
                                        <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                            Pet System
                                        </h2>
                                    </div>
                                </div>
                                <div className="p-6 relative">
                                    <div className="grid grid-cols-1 gap-6">
                                        <div className="space-y-4">
                                            <div className="bg-black/20 rounded-lg p-4 border border-white/5">
                                                <div className="flex items-center justify-between mb-4">
                                                    <h4 className="text-white font-medium">
                                                        Quick Commands
                                                    </h4>
                                                    <span className="text-[10px] font-medium bg-evict-primary/10 text-evict-primary px-2 py-0.5 rounded-full">
                                                        NEW
                                                    </span>
                                                </div>
                                                <div className="space-y-2 font-mono text-sm">
                                                    <div className="text-evict-primary/80">
                                                        ;pet adopt dog Buddy
                                                    </div>
                                                    <div className="text-evict-primary/80">
                                                        ;pet feed Buddy
                                                    </div>
                                                    <div className="text-evict-primary/80">
                                                        ;pet adventure Buddy
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="grid grid-cols-2 gap-3">
                                                {[
                                                    {
                                                        label: "Total Pets",
                                                        value: <Counter from={0} to={25000} />
                                                    },
                                                    {
                                                        label: "Pet Types",
                                                        value: <Counter from={0} to={12} />
                                                    }
                                                ].map((stat, i) => (
                                                    <div
                                                        key={i}
                                                        className="bg-white/[0.02] rounded-lg p-3 border border-white/5">
                                                        <div className="text-sm text-white/40 mb-1">
                                                            {stat.label}
                                                        </div>
                                                        <div className="text-evict-primary font-medium">
                                                            {stat.value}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        </motion.div>

                        <motion.div
                            variants={container}
                            className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
                            <motion.div
                                variants={item}
                                className="group relative bg-gradient-to-br from-white/[0.03] to-transparent border border-white/5 rounded-xl overflow-hidden">
                                <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-evict-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                <div className="border-b border-white/5 p-6 relative">
                                    <div className="flex items-center gap-3">
                                        <Trophy className="w-6 h-6 text-evict-primary" />
                                        <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                            Leaderboards
                                        </h2>
                                    </div>
                                </div>
                                <div className="p-6 relative">
                                    <div className="space-y-4">
                                        {[
                                            {
                                                rank: 1,
                                                name: "Player One",
                                                balance: "2.5M",
                                                businesses: 5
                                            },
                                            {
                                                rank: 2,
                                                name: "Player Two",
                                                balance: "1.8M",
                                                businesses: 4
                                            },
                                            {
                                                rank: 3,
                                                name: "Player Three",
                                                balance: "1.2M",
                                                businesses: 3
                                            }
                                        ].map((player, i) => (
                                            <div
                                                key={i}
                                                className="group/player relative bg-black/20 rounded-lg p-4 border border-white/5 hover:border-evict-primary/20 transition-colors duration-300">
                                                <div className="flex items-center gap-4">
                                                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-evict-primary/10">
                                                        <span className="text-evict-primary font-bold">
                                                            #{player.rank}
                                                        </span>
                                                    </div>
                                                    <div className="flex-1">
                                                        <div className="text-white font-medium">
                                                            {player.name}
                                                        </div>
                                                        <div className="text-sm text-white/40">
                                                            {player.businesses} Businesses
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="text-evict-primary font-bold">
                                                            {player.balance}
                                                        </div>
                                                        <div className="text-sm text-white/40">
                                                            Balance
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>

                            <motion.div
                                variants={item}
                                className="group relative bg-gradient-to-br from-white/[0.03] to-transparent border border-white/5 rounded-xl overflow-hidden">
                                <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-evict-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                <div className="border-b border-white/5 p-6 relative">
                                    <div className="flex items-center gap-3">
                                        <Award className="w-6 h-6 text-evict-primary" />
                                        <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                            Achievements
                                        </h2>
                                    </div>
                                </div>
                                <div className="p-6 relative">
                                    <div className="grid grid-cols-2 gap-4">
                                        {[
                                            {
                                                icon: <Star className="w-4 h-4" />,
                                                name: "First Million",
                                                description: "Earn 1,000,000 coins",
                                                reward: "10,000 XP"
                                            },
                                            {
                                                icon: <Building2 className="w-4 h-4" />,
                                                name: "Business Tycoon",
                                                description: "Own 5 businesses",
                                                reward: "Unique Role"
                                            },
                                            {
                                                icon: <Gift className="w-4 h-4" />,
                                                name: "Generous Soul",
                                                description: "Gift 100,000 coins",
                                                reward: "Special Badge"
                                            },
                                            {
                                                icon: <BarChart className="w-4 h-4" />,
                                                name: "High Roller",
                                                description: "Win 5M from gambling",
                                                reward: "Exclusive Title"
                                            }
                                        ].map((achievement, i) => (
                                            <div
                                                key={i}
                                                className="group/achievement bg-black/20 rounded-lg p-4 border border-white/5 hover:border-evict-primary/20 transition-colors duration-300">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <div className="w-6 h-6 rounded-full bg-evict-primary/10 flex items-center justify-center text-evict-primary">
                                                        {achievement.icon}
                                                    </div>
                                                    <h4 className="text-white font-medium">
                                                        {achievement.name}
                                                    </h4>
                                                </div>
                                                <p className="text-sm text-white/40 mb-2">
                                                    {achievement.description}
                                                </p>
                                                <div className="text-sm text-evict-primary">
                                                    Reward: {achievement.reward}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        </motion.div>

                        <motion.div
                            variants={container}
                            className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
                            {[
                                {
                                    icon: <History className="w-6 h-6 text-evict-primary" />,
                                    title: "Transaction History",
                                    description:
                                        "Track all your financial activities, including income, expenses, and transfers.",
                                    command: ";history"
                                },
                                {
                                    icon: <Briefcase className="w-6 h-6 text-evict-primary" />,
                                    title: "Business Analytics",
                                    description:
                                        "View detailed statistics about your business performance and employee productivity.",
                                    command: ";business stats"
                                },
                                {
                                    icon: <Gift className="w-6 h-6 text-evict-primary" />,
                                    title: "Daily Rewards",
                                    description:
                                        "Claim daily rewards and bonuses to boost your economy progress.",
                                    command: ";daily"
                                }
                            ].map((feature, i) => (
                                <motion.div
                                    key={i}
                                    variants={item}
                                    className="group relative bg-gradient-to-br from-white/[0.03] to-transparent border border-white/5 rounded-xl p-6 hover:border-evict-primary/20 transition-colors duration-300">
                                    <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-evict-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                    <div className="relative">
                                        <div className="flex items-center gap-3 mb-4">
                                            {feature.icon}
                                            <h3 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-evict-primary">
                                                {feature.title}
                                            </h3>
                                        </div>
                                        <p className="text-white/60 mb-4">{feature.description}</p>
                                        <div className="font-mono text-sm text-evict-primary/80">
                                            {feature.command}
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </motion.div>

                        <motion.div
                            key="server-cta"
                            initial={{ opacity: 0, x: 20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true, margin: "-100px" }}
                            transition={{ duration: 0.4 }}
                            className="relative mt-24 lg:pl-12 text-center lg:text-left">
                            <div className="absolute inset-0 rounded-3xl bg-gradient-to-r from-evict-primary/10 via-transparent to-evict-primary/10 opacity-20 blur-3xl -z-10" />
                            <div className="relative">
                                <span className="text-4xl font-bold bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent mb-4 block">
                                    Start Your Economy Journey
                                </span>
                                <div className="flex flex-col lg:flex-row items-center gap-8 mt-8">
                                    <div className="flex-1 space-y-4">
                                        <p className="text-white/60 text-xl">
                                            Join thousands of servers already using Evict&apos;s economy system
                                        </p>
                                        <div className="flex flex-wrap gap-6 justify-center lg:justify-start text-white/40">
                                            <div className="flex items-center gap-2">
                                                <PiggyBank className="w-5 h-5 text-evict-primary" />
                                                Start with 1,000 coins
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Building2 className="w-5 h-5 text-evict-primary" />
                                                Create your business
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Trophy className="w-5 h-5 text-evict-primary" />
                                                Climb leaderboards
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
                    </motion.div>
                </div>
            </motion.div>
        </AnimatePresence>
    )
}
