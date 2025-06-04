"use client"
import { MeshGradient } from "@/components/(global)/GradientMesh"
import Particles from "@/components/ui/particles"
import Navbar from "@/components/(global)/navbar/Navbar"
import "@/styles/globals.css"
import { motion } from "framer-motion"
import Image from "next/image"
import { ReactNode, useEffect, useState } from "react"
import { LuPanelLeftOpen, LuRadiation } from "react-icons/lu"
import { RiDiscordLine } from "react-icons/ri"
import { ImEmbed2 } from "react-icons/im"
import ShineBorder from "@/components/ui/shine-border"

import marly from "../../../public/marly.gif"

const fetchShards = async () => {
    const response = await fetch(`https://network.skunkk.xyz/status`)
    if (!response.ok) {
        console.error("Failed to fetch shard data")
        return []
    }
    const data = await response.json()
    return data.shards.map((shard: any) => ({
        id: shard.shard_id,
        guilds: shard.server_count,
        users: shard.cached_user_count,
        ping: shard.latency,
        uptime: shard.uptime
    }))
}

export default function Home() {
    const [shards, setShards] = useState<IShard[]>([])
    const [totalUsers, setTotalUsers] = useState<number>(0)
    const [totalGuilds, setTotalGuilds] = useState<number>(0)

    useEffect(() => {
        const fetchData = async () => {
            const fetchedShards = await fetchShards()

            if (fetchedShards.length === 0) {
                console.error("No shard data available")
            } else {
                const totalUsers = fetchedShards.reduce(
                    (acc: number, shard: IShard) => acc + shard.users,
                    0
                )
                const totalGuilds = fetchedShards.reduce(
                    (acc: number, shard: IShard) => acc + shard.guilds,
                    0
                )

                setTotalUsers(totalUsers)
                setTotalGuilds(totalGuilds)
            }

            setShards(fetchedShards)
        }

        fetchData()
    }, [])

    const fadeUpVariants = {
        hidden: { opacity: 0, y: 90 },
        visible: { opacity: 1, y: 0 }
    }

    return (
        <>
            <Particles className="fixed inset-0" />
            <MeshGradient />    
            <Navbar />
            <div className="flex flex-col h-screen w-screen items-center justify-center">
                <motion.div
                    initial={{ opacity: 0, y: 500, scale: 0.5 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ ease: "easeInOut", duration: 1 }}
                    className="rounded-lg pb-3">
                    <Image 
                        src={marly} 
                        alt="marly" 
                        width={300} 
                        height={300} 
                        className="rounded-full"
                    />
                </motion.div>
                <motion.span
                    initial="hidden"
                    animate="visible"
                    variants={fadeUpVariants}
                    transition={{
                        ease: "easeInOut",
                        duration: 0.8,
                        delay: 0.7
                    }}
                    className="text-lg pb-10 font-medium text-[#6A6F71] text-center">
                    serving{" "}
                    <span className="text-[#D6D6D6] font-semibold">
                        {totalUsers.toLocaleString() || "???"}
                    </span>{" "}
                    users across{" "}
                    <span className="text-[#D6D6D6] font-semibold">
                        {totalGuilds.toLocaleString() || "???"}
                    </span>{" "}
                    servers
                </motion.span>
                <div className="flex flex-col gap-3 sm:gap-6">
                    <div className="flex flex-row gap-3 sm:gap-6">
                        <motion.div
                            initial="hidden"
                            animate="visible"
                            variants={fadeUpVariants}
                            transition={{
                                ease: "easeInOut",
                                duration: 0.8,
                                delay: 0.9
                            }}>
                            <SplashItem name="cmds" link="/commands" icon={<LuPanelLeftOpen />} />
                        </motion.div>
                        <motion.div
                            initial="hidden"
                            animate="visible"
                            variants={fadeUpVariants}
                            transition={{
                                ease: "easeInOut",
                                duration: 0.8,
                                delay: 0.91
                            }}>
                            <SplashItem
                                name="discord"
                                link="https://discord.com/marly"
                                icon={<RiDiscordLine />}
                            />
                        </motion.div>
                    </div>
                    <div className="flex flex-row gap-3 sm:gap-6">
                        <motion.div
                            initial="hidden"
                            animate="visible"
                            variants={fadeUpVariants}
                            transition={{
                                ease: "easeInOut",
                                duration: 0.8,
                                delay: 0.92
                            }}>
                            <SplashItem
                                name="docs"
                                link="https://docs.marly.bot/"
                                icon={<LuRadiation />}
                            />
                        </motion.div>
                        <motion.div
                            initial="hidden"
                            animate="visible"
                            variants={fadeUpVariants}
                            transition={{
                                ease: "easeInOut",
                                duration: 0.8,
                                delay: 0.93
                            }}>
                            <SplashItem
                                name="embeds"
                                link="/embeds"
                                icon={<ImEmbed2 />}
                            />
                        </motion.div>
                    </div>
                </div>
            </div>
        </>
    )
}

const SplashItem = ({ name, link, icon }: { name: string; link: string; icon: ReactNode }) => {
    return (
        <ShineBorder 
            borderRadius={16} 
            duration={4} 
            color={["#ffaa40", "#9c40ff"]}
            className="w-[20vw] sm:w-[150px] hover:scale-105 transition-transform duration-500 !bg-[#1E1F1F] !bg-opacity-90"
        >
            <a
                href={link}
                className="flex flex-row gap-2 items-center text-neutral-300 font-semibold hover:bg-opacity-50 transition-colors duration-500 py-[1rem] px-4"
            >
                {icon}
                {name}
            </a>
        </ShineBorder>
    )
}

interface IShard {
    id: string
    guilds: number
    users: number
    ping: number
    uptime: number
}