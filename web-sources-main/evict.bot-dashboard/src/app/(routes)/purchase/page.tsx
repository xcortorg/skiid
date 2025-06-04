"use client"

import { Dialog } from "@headlessui/react"
import localFont from "next/font/local"
import Image from "next/image"
import Link from "next/link"
import { useState } from "react"
import { BiLockAlt } from "react-icons/bi"
import { BsCreditCard, BsServer } from "react-icons/bs"
import { FaBitcoin, FaEthereum, FaWrench } from "react-icons/fa"
import { HiCheck, HiLightningBolt } from "react-icons/hi"
import { IoShieldCheckmark } from "react-icons/io5"
import { MdPalette } from "react-icons/md"
import { RiDiscordLine, RiRobot2Line } from "react-icons/ri"
import { RxCross2 } from "react-icons/rx"
import { SiLitecoin, SiXrp } from "react-icons/si"

const clash = localFont({
    src: [
        {
            path: "../../../../public/fonts/ClashDisplay-Bold.otf",
            weight: "700",
            style: "normal"
        },
        {
            path: "../../../../public/fonts/ClashDisplay-Semibold.otf",
            weight: "600",
            style: "normal"
        },
        {
            path: "../../../../public/fonts/ClashDisplay-Medium.otf",
            weight: "500",
            style: "normal"
        }
    ],
    variable: "--font-clash"
})

export default function PurchasePage() {
    const [donatorModal, setDonatorModal] = useState(false)
    const [instanceModal, setInstanceModal] = useState(false)

    return (
        <>
            <div className={`${clash.variable} relative w-full`}>
                <div className="relative min-h-screen bg-gradient-to-br from-[#0B0B1A] via-[#1F1147] to-[#0B0B1A]">
                    <div className="relative max-w-7xl mx-auto px-4 pt-32">
                        <div className="text-center max-w-5xl mx-auto">
                            <h1 className="font-clash font-bold text-7xl md:text-8xl mb-4">
                                Evict Instances
                                <br />
                                <span className="text-[#7289DA]">Are Here.</span>
                            </h1>
                            <div className="space-y-4 mb-12">
                                <p className="text-xl md:text-2xl text-white/60">
                                    Communities need their own customized bot with customized
                                    features.
                                </p>
                                <p className="text-xl md:text-2xl text-white/60">
                                    This is where Evict Premium comes into play.
                                </p>
                            </div>
                            <a
                                href="#plans"
                                className="bg-white hover:bg-white/90 text-black font-medium px-8 py-4 rounded-full 
                                 transition-all transform hover:scale-[1.02] group">
                                Explore plans
                                <span className="inline-block transition-transform group-hover:translate-x-1">
                                    →
                                </span>
                            </a>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto mt-24">
                            <div className="relative group h-full transform-gpu will-change-transform">
                                <div className="absolute inset-0 bg-[#1F1147]/50 rounded-[32px] blur-2xl group-hover:blur-3xl transition-all duration-300 will-change-[filter]" />
                                <div className="relative h-full bg-[#1F1147]/20 backdrop-blur-2xl rounded-[32px] p-8 border border-white/10">
                                    <h3 className="font-clash font-semibold text-2xl mb-4">
                                        Your custom unique command(s)*
                                    </h3>
                                    <p className="text-white/60 leading-relaxed">
                                        Request any custom command from us, and if our development
                                        team can do it, we&apos;ll add it to your own-custom bot.
                                        Don&apos;t like it? We&apos;ll create another one for you.
                                    </p>
                                </div>
                            </div>

                            <div className="relative group h-full transform-gpu will-change-transform">
                                <div className="absolute inset-0 bg-[#1F1147]/50 rounded-[32px] blur-2xl group-hover:blur-3xl transition-all duration-300 will-change-[filter]" />
                                <div className="relative h-full bg-[#1F1147]/20 backdrop-blur-2xl rounded-[32px] p-8 border border-white/10">
                                    <h3 className="font-clash font-semibold text-2xl mb-4">
                                        Your customisation, taken to the next level.
                                    </h3>
                                    <p className="text-white/60 leading-relaxed">
                                        Growing a big community? Want a fancy Discord bot with
                                        1,000+ commands AND custom branding? You&apos;re in the
                                        right place.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="mt-32 max-w-7xl mx-auto px-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-24">
                        {[
                            { number: "1,000+", label: "Commands" },
                            { number: "99.9%", label: "Uptime" },
                            { number: "24/7", label: "Support" },
                            { number: "2,600+", label: "Servers" }
                        ].map((stat, i) => (
                            <div key={i} className="bg-[#0B0C0C] rounded-2xl p-6 text-center">
                                <div className="font-clash font-bold text-4xl md:text-5xl mb-2">
                                    {stat.number}
                                </div>
                                <div className="text-white/60">{stat.label}</div>
                            </div>
                        ))}
                    </div>

                    <div className="grid md:grid-cols-3 gap-8 mb-24">
                        {[
                            {
                                icon: <HiLightningBolt className="w-8 h-8 text-yellow-400" />,
                                title: "Full Command Access",
                                description:
                                    "Access to all 844 commands and features, from moderation to fun interactions."
                            },
                            {
                                icon: <MdPalette className="w-8 h-8 text-orange-400" />,
                                title: "Complete Customization",
                                description:
                                    "Custom name, avatar, status & description. Make it truly yours."
                            },
                            {
                                icon: <FaWrench className="w-8 h-8 text-blue-400" />,
                                title: "System Embeds",
                                description:
                                    "Customization of 15 system embeds to match your server's theme."
                            },
                            {
                                icon: <BiLockAlt className="w-8 h-8 text-yellow-400" />,
                                title: "Server Authentication",
                                description:
                                    "2 server authentications with more available upon justification."
                            },
                            {
                                icon: <BsServer className="w-8 h-8 text-white" />,
                                title: "Dedicated Hosting",
                                description:
                                    "Hosted on dedicated US servers for optimal latency and performance."
                            },
                            {
                                icon: <IoShieldCheckmark className="w-8 h-8 text-blue-400" />,
                                title: "Enterprise Security",
                                description:
                                    "System access limited to Evict administrators and senior staff."
                            }
                        ].map((feature, i) => (
                            <div key={i} className="bg-[#0B0C0C] rounded-2xl p-8">
                                <div className="mb-4">{feature.icon}</div>
                                <h3 className="font-clash font-semibold text-xl mb-3">
                                    {feature.title}
                                </h3>
                                <p className="text-white/60">{feature.description}</p>
                            </div>
                        ))}
                    </div>

                    <div className="relative group mb-24">
                        <div className="absolute inset-0 bg-[#0B0C0C]/30 rounded-[32px] blur-2xl" />
                        <div className="relative bg-[#0B0C0C]/20 backdrop-blur-2xl rounded-[32px] p-8 md:p-12 border border-white/10">
                            <div className="grid md:grid-cols-2 gap-12 items-center">
                                <div>
                                    <h2 className="font-clash font-bold text-3xl md:text-4xl mb-6">
                                        Enterprise-Grade Infrastructure
                                    </h2>
                                    <div className="space-y-4">
                                        <p className="text-white/60">
                                            Your instance runs on dedicated US servers, ensuring
                                            optimal performance and reliability. Hosted on 
                                            NYCDEDICATED in New York, New York.
                                        </p>
                                        <ul className="space-y-3">
                                            <li className="flex items-center gap-3">
                                                <div className="w-2 h-2 rounded-full bg-green-400" />
                                                <span>99.9% Guaranteed uptime</span>
                                            </li>
                                            <li className="flex items-center gap-3">
                                                <div className="w-2 h-2 rounded-full bg-green-400" />
                                                <span>24/7 System monitoring</span>
                                            </li>
                                            <li className="flex items-center gap-3">
                                                <div className="w-2 h-2 rounded-full bg-green-400" />
                                                <span>Automated backup systems</span>
                                            </li>
                                            <li className="flex items-center gap-3">
                                                <div className="w-2 h-2 rounded-full bg-green-400" />
                                                <span>10gbps ddos protection</span>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                                <div className="relative">
                                    <Image
                                        src="/nycdedicated.webp"
                                        alt="NYCDEDICATED Datacenter"
                                        width={500}
                                        height={300}
                                        className="rounded-2xl w-full h-full object-cover"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="mt-32 mb-24 max-w-7xl mx-auto px-4">
                    <h2 className="font-clash font-bold text-4xl text-center mb-4" id="plans">
                        All of our Plans
                    </h2>
                    <p className="text-white/60 text-center mb-16">
                        Check out Evict&apos;s Premium plans and instance offering
                    </p>

                    <div className="relative overflow-x-auto">
                        <div className="min-w-[768px] md:min-w-full">
                            <div className="grid grid-cols-4 gap-4 md:gap-8 mb-12">
                                <div className="min-w-[200px]" />
                                {[
                                    {
                                        title: "Free",
                                        price: "0€ /Lifetime",
                                        action: "Sign Up",
                                        href: "https://evict.bot/invite",
                                        style: "bg-[#1F1F1F] hover:bg-[#1F1F1F]/80"
                                    },
                                    {
                                        title: "Donator",
                                        price: "Any amount",
                                        action: "Purchase",
                                        onClick: () => setDonatorModal(true),
                                        style: "bg-white hover:bg-white/90 text-black"
                                    },
                                    {
                                        title: "Instance",
                                        price: "17.5€ + 3.5€/month",
                                        action: "Purchase",
                                        onClick: () => setInstanceModal(true),
                                        style: "bg-gray-400 cursor-not-allowed",
                                        disabled: true,
                                        tooltip: "Instances are temporarily on hold"
                                    }
                                ].map((plan, i) => (
                                    <div key={i} className="text-center min-w-[180px]">
                                        <h3 className="font-clash font-semibold text-2xl mb-2">
                                            {plan.title}
                                        </h3>
                                        <p className="text-white/60 mb-4">{plan.price}</p>
                                        {plan.href ? (
                                            <Link
                                                href={plan.href}
                                                className={`inline-block w-full ${plan.style} py-3 px-6 rounded-full transition-all transform hover:scale-[1.02]`}>
                                                {plan.action}
                                            </Link>
                                        ) : (
                                            <button
                                                onClick={plan.onClick}
                                                className={`w-full ${plan.style} py-3 px-6 rounded-full transition-all transform hover:scale-[1.02]`}
                                                disabled={plan.disabled}
                                                title={plan.tooltip}>
                                                {plan.action}
                                            </button>
                                        )}
                                    </div>
                                ))}
                            </div>

                            {[
                                "Basic Commands",
                                "Premium Commands",
                                "Reskin Option",
                                "Custom Avatars",
                                "Custom Banner",
                                "Custom Description & Status",
                                "Automatic Deployment",
                                "System Embeds Editing"
                            ].map((feature, i) => (
                                <div
                                    key={i}
                                    className="grid grid-cols-4 gap-4 md:gap-8 py-4 border-t border-white/5">
                                    <div className="font-medium min-w-[200px]">{feature}</div>
                                    <div className="flex justify-center min-w-[180px]">
                                        {i === 0 ? (
                                            <HiCheck className="w-5 h-5 text-[#7289DA]" />
                                        ) : (
                                            <RxCross2 className="w-5 h-5 text-white/20" />
                                        )}
                                    </div>
                                    <div className="flex justify-center min-w-[180px]">
                                        {i <= 2 ? (
                                            <HiCheck className="w-5 h-5 text-[#7289DA]" />
                                        ) : (
                                            <RxCross2 className="w-5 h-5 text-white/20" />
                                        )}
                                    </div>
                                    <div className="flex justify-center min-w-[180px]">
                                        <HiCheck className="w-5 h-5 text-[#7289DA]" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="md:hidden text-center text-white/40 mt-4 text-sm">
                        Scroll horizontally to see more →
                    </div>
                </div>
            </div>

            <Dialog
                open={donatorModal}
                onClose={() => setDonatorModal(false)}
                className="relative z-50">
                <div className="fixed inset-0 bg-black/80" aria-hidden="true" />
                <div className="fixed inset-0 flex items-center justify-center p-4">
                    <Dialog.Panel className="bg-[#0B0C0C] rounded-2xl p-6 max-w-md w-full">
                        <Dialog.Title className="font-clash font-bold text-2xl mb-4">
                            Choose Payment Method
                        </Dialog.Title>

                        <div className="space-y-4">
                            <a
                                href="https://donate.stripe.com/cN26ra4tXgrg3T2cMR"
                                target="_blank"
                                className="flex items-center justify-between w-full bg-white text-black px-4 py-3 rounded-xl hover:bg-white/90">
                                <span className="flex items-center gap-2">
                                    <BsCreditCard className="w-5 h-5" />
                                    Card & Cashapp Payment
                                </span>
                                <span>→</span>
                            </a>

                            <div className="border-t border-white/10 pt-4">
                                <h3 className="font-medium mb-3">Crypto Payment</h3>
                                <div className="space-y-2 text-sm text-white/60">
                                    <p className="flex items-center gap-2">
                                        <FaBitcoin className="text-[#F7931A]" /> BTC:
                                        bc1qjpgep0qqjt60a2my977yk83jf9nnrce7t07x2u
                                    </p>
                                    <p className="flex items-center gap-2">
                                        <FaEthereum className="text-[#627EEA]" /> ETH:
                                        0xf1A2E8b1bDAf98D26F6c2A72d5d36448325c97E3
                                    </p>
                                    <p className="flex items-center gap-2">
                                        <SiXrp /> XRP: rhK4NTAyZC3wxi5Yyfj7B3rz3Cgr3F35oN
                                    </p>
                                    <p className="flex items-center gap-2">
                                        <SiLitecoin className="text-[#345D9D]" /> LTC:
                                        ltc1qfl5pg0ds68p9fm8h4tez8qm87xdhl64n3xrttv
                                    </p>
                                </div>
                                <p className="mt-4 text-sm text-white/60">
                                    Minimum donation: $1. For crypto payments, please open a ticket
                                    in our support server with your payment hash.
                                </p>
                            </div>
                        </div>
                    </Dialog.Panel>
                </div>
            </Dialog>

            <Dialog
                open={instanceModal}
                onClose={() => setInstanceModal(false)}
                className="relative z-50">
                <div className="fixed inset-0 bg-black/80" aria-hidden="true" />
                <div className="fixed inset-0 flex items-center justify-center p-4">
                    <Dialog.Panel className="bg-[#0B0C0C] rounded-2xl p-6 max-w-md w-full">
                        <Dialog.Title className="font-clash font-bold text-2xl mb-4">
                            Instance Payment
                        </Dialog.Title>

                        <div className="space-y-4">
                            <div>
                                <h3 className="font-medium mb-3">Card & Cashapp Payment</h3>
                                <div className="space-y-2">
                                    <a
                                        href="https://buy.stripe.com/8wMcPygcFej81KU006"
                                        target="_blank"
                                        className="flex items-center justify-between w-full bg-white text-black px-4 py-3 rounded-xl hover:bg-white/90">
                                        <span>Instance Setup ($17.5)</span>
                                        <span>→</span>
                                    </a>
                                    <a
                                        href="https://buy.stripe.com/aEU5n64tXcb02OYeV1"
                                        target="_blank"
                                        className="flex items-center justify-between w-full bg-white text-black px-4 py-3 rounded-xl hover:bg-white/90">
                                        <span>Monthly Hosting ($3)</span>
                                        <span>→</span>
                                    </a>
                                </div>
                            </div>

                            <div className="border-t border-white/10 pt-4">
                                <h3 className="font-medium mb-3">Crypto Payment</h3>
                                <div className="space-y-2 text-sm text-white/60">
                                    <p className="flex items-center gap-2">
                                        <FaBitcoin className="text-[#F7931A]" /> BTC:
                                        bc1qjpgep0qqjt60a2my977yk83jf9nnrce7t07x2u
                                    </p>
                                    <p className="flex items-center gap-2">
                                        <FaEthereum className="text-[#627EEA]" /> ETH:
                                        0xf1A2E8b1bDAf98D26F6c2A72d5d36448325c97E3
                                    </p>
                                    <p className="flex items-center gap-2">
                                        <SiXrp /> XRP: rhK4NTAyZC3wxi5Yyfj7B3rz3Cgr3F35oN
                                    </p>
                                    <p className="flex items-center gap-2">
                                        <SiLitecoin className="text-[#345D9D]" /> LTC:
                                        ltc1qfl5pg0ds68p9fm8h4tez8qm87xdhl64n3xrttv
                                    </p>
                                </div>
                                <p className="mt-4 text-sm text-white/60">
                                    Minimum donation: $1. For crypto payments, please open a ticket
                                    in our support server with your payment hash.
                                </p>
                            </div>

                            <p className="text-sm text-white/60">
                                Note: Stripe payments are automated. Crypto payments require manual
                                verification through support.
                            </p>
                        </div>
                    </Dialog.Panel>
                </div>
            </Dialog>

            <div className="text-center max-w-3xl mx-auto mt-32 mb-24 px-4">
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
            </div>
        </>
    )
}
