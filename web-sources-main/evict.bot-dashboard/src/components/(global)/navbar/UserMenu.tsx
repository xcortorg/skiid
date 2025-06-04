"use client"

import { motion } from "framer-motion"
import { Crown, Sparkles } from "lucide-react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import { CgClose } from "react-icons/cg"
import { MdMenu } from "react-icons/md"

const UserMenu = () => {
    const router = useRouter()
    const pathname = usePathname()
    const [mounted, setMounted] = useState(false)
    const [isBurgerMenuOpen, setIsBurgerMenuOpen] = useState(false)
    const [showBetaPopup, setShowBetaPopup] = useState(false)

    useEffect(() => {
        setMounted(true)
        if (pathname === "/") {
            setShowBetaPopup(localStorage.getItem("betaPopupDismissed") !== "true")
        }
    }, [pathname])

    useEffect(() => {
        if (mounted) {
            if (pathname === "/") {
                setShowBetaPopup(localStorage.getItem("betaPopupDismissed") !== "true")
            } else {
                setShowBetaPopup(false)
            }
        }
    }, [pathname, mounted])

    const dismissPopup = () => {
        setShowBetaPopup(false)
        localStorage.setItem("betaPopupDismissed", "true")
    }

    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth > 1025) {
                setIsBurgerMenuOpen(false)
            }
        }

        handleResize()
        window.addEventListener("resize", handleResize)
        return () => window.removeEventListener("resize", handleResize)
    }, [])

    return (
        <>
            {/* {showBetaPopup && (
                <>
                    <div
                        className="fixed inset-0 bg-black bg-opacity-50 z-[50000] backdrop-blur-sm"
                        onClick={dismissPopup}
                    />
                    <div className="fixed inset-0 z-[50001] flex items-center justify-center">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="bg-evict-200 border border-evict-card-border p-6 rounded-xl shadow-lg max-w-md mx-4">
                            <div className="flex justify-between items-start mb-4">
                                <div className="bg-white/10 p-2 rounded-lg">
                                    <Sparkles className="w-6 h-6 text-evict-pink" />
                                </div>
                                <button
                                    onClick={dismissPopup}
                                    className="text-white/60 hover:text-white">
                                    <CgClose size={24} />
                                </button>
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">
                                Dashboard Open Beta
                            </h2>
                            <p className="text-white/60 mb-4">
                                Our new dashboard is now available in open beta! Try out the latest
                                features and help us improve by providing feedback.
                            </p>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => {
                                        dismissPopup()
                                        router.push("/beta")
                                    }}
                                    className="flex-1 bg-evict-pink text-white px-4 py-2 rounded-lg font-medium hover:bg-evict-pink/90 transition-colors">
                                    Join Beta
                                </button>
                                <button
                                    onClick={dismissPopup}
                                    className="px-4 py-2 text-white/60 hover:text-white transition-colors">
                                    Maybe Later
                                </button>
                            </div>
                        </motion.div>
                    </div>
                </>
            )} */}

            {isBurgerMenuOpen && (
                <>
                    <div
                        className="fixed inset-0 bg-black bg-opacity-50 z-[50000] backdrop-blur-sm"
                        onClick={() => setIsBurgerMenuOpen(false)}
                    />
                    <BurgerMenu onClose={() => setIsBurgerMenuOpen(false)} />
                </>
            )}
            <div className="flex flex-row items-center justify-center space-x-4">
                <div className="block lg:hidden">
                    <MdMenu
                        size={32}
                        className="hover:cursor-pointer hover:text-evict-pink"
                        onClick={() => setIsBurgerMenuOpen(!isBurgerMenuOpen)}
                    />
                </div>
                {/* <Link
                    href="/purchase"
                    className="text-zinc-500 hover:text-evict-pink transition-colors">
                    <Crown className="w-5 h-5" />
                </Link> */}
                <button
                    onClick={() => router.push("/purchase")}
                    className="bg-[#4B5563] px-4 sm:px-8 py-2 flex items-center space-x-2 rounded-full font-medium text-sm sm:text-base transition-all duration-200 hover:bg-[#404754] text-white">
                    <Sparkles className="w-4 h-4 sm:w-5 sm:h-5" />
                    <span className="font-normal hidden sm:inline">Purchase</span>
                    <span className="font-normal sm:hidden">Purchase</span>
                </button>
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
                destination: "https://embeds.evict.bot",
                isActive: pathname == "https://embeds.evict.bot"
            },
            {
                label: "Docs",
                destination: "https://docs.evict.bot",
                isActive: pathname == "https://docs.evict.bot"
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
                    className="bg-evict-200 border -mt-40 border-evict-card-border w-[90%] px-2 rounded-xl shadow-lg">
                    <div className="flex flex-row justify-between items-center gap-6 pt-10 px-4">
                        <h1 className="font-bold text-white text-4xl">Menu</h1>
                        <CgClose
                            size={24}
                            className="ml-auto hover:cursor-pointer hover:text-evict-pink"
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
                                    className={`flex items-center h-14 bg-evict-300 rounded-md ${
                                        route.isActive
                                            ? "text-evict-pink bg-evict-200"
                                            : "text-evict-700 hover:bg-evict-dim hover:text-white"
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
