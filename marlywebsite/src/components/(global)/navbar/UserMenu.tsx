"use client"

import { motion } from "framer-motion"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import { CgClose } from "react-icons/cg"
import { FaDiscord } from "react-icons/fa"
import { MdMenu } from "react-icons/md"

const UserMenu = () => {
    const router = useRouter()
    const [isBurgerMenuOpen, setIsBurgerMenuOpen] = useState(false)

    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth > 1025) {
                setIsBurgerMenuOpen(false)
            }
        }

        handleResize()

        window.addEventListener("resize", handleResize)

        return () => {
            window.removeEventListener("resize", handleResize)
        }
    }, [])
    return (
        <>
            {isBurgerMenuOpen && (
                <>
                    <div
                        className="fixed inset-0 bg-black bg-opacity-50 z-[50000] backdrop-blur-sm"
                        onClick={() => setIsBurgerMenuOpen(false)}
                    />
                    <BurgerMenu onClose={() => setIsBurgerMenuOpen(false)} />
                </>
            )}
            <div className="flex flex-row items-center justify-center space-x-2 px-14">
                <div className="block lg:hidden">
                    <MdMenu
                        size={32}
                        className="hover:cursor-pointer hover:text-marly-main"
                        onClick={() => setIsBurgerMenuOpen(!isBurgerMenuOpen)}
                    />
                </div>
                <Link
                    href="https://marly.bot/discord"
                    className="hidden lg:flex items-center px-4 py-3.5 text-sm font-semibold transition duration-300 ease-linear bg-[#5865F2] hover:ring-2 hover:ring-[#5865F2] sm:px-5 rounded-full">
                    <FaDiscord className="inline-block w-5 h-5 sm:-ml-1" />
                    <span className="hidden text-[15px] sm:inline-block ml-3.5">Discord</span>
                </Link>
            </div>
        </>
    )
}

const BurgerMenu = ({ onClose }: { onClose: () => void }) => {
    const pathname = usePathname()
    const routes = useMemo(
        () => [
            {
                label: "Commands",
                destination: "/commands",
                isActive: pathname == "/commands"
            },
            {
                label: "Embeds",
                destination: "https://embeds.marly.bot",
                isActive: pathname == "https://embeds.marly.bot"
            },
            {
                label: "Docs",
                destination: "https://docs.marly.bot",
                isActive: pathname == "https://docs.marly.bot"
            },
            {
                label: "Invite",
                destination: "/invite",
                isActive: pathname == "/invite"
            },
            {
                label: "Status",
                destination: "/status",
                isActive: pathname == "/status"
            }
        ],
        [pathname]
    )
    return (
        <>
            <div className="fixed inset-0 z-[9999999999] flex items-center justify-center">
                <motion.div
                    initial={{ opacity: 0, y: 40, scale: 0.7 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 20 }}
                    transition={{
                        ease: "linear",
                        duration: 0.2
                    }}
                    className="bg-marly-200 border -mt-40 border-marly-card-border w-[90%] px-2 rounded-xl shadow-lg">
                    <div className="flex flex-row justify-between items-center gap-6 pt-10 px-4">
                        <h1 className="font-bold text-white text-4xl">Menu</h1>
                        <CgClose
                            size={24}
                            className="ml-auto hover:cursor-pointer hover:text-marly-main"
                            onClick={onClose}
                        />
                    </div>
                    <div className="flex flex-col gap-4 px-4 pt-10 pb-10">
                        {routes.map(route => {
                            return (
                                <Link
                                    href={route.destination}
                                    key={route.label}
                                    onClick={onClose}
                                    className={`flex items-center h-14 bg-marly-300 rounded-md ${
                                        route.isActive
                                            ? "text-marly-main bg-marly-200"
                                            : "text-marly-700 hover:bg-marly-dim hover:text-white"
                                    }`}>
                                    <span className="text-base font-medium pl-5">
                                        {route.label}
                                    </span>
                                </Link>
                            )
                        })}
                    </div>
                </motion.div>
            </div>
        </>
    )
}

export default UserMenu
