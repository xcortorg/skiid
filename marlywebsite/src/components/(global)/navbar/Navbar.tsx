"use client"

import Loading from "@/app/(routes)/loading"
import { AnimatePresence } from "framer-motion"
import Image from "next/image"
import Link from "next/link"
import { usePathname } from "next/navigation"
import router from "next/router"
import { useMemo, useState } from "react"
import { FaDiscord } from "react-icons/fa"
import marly from "../../../../public/marly.gif"

interface NavbarProps {
    children?: React.ReactNode
}

const Navbar: React.FC<NavbarProps> = ({ children }) => {
    const [isLoading, setIsLoading] = useState(true)
    const pathname = usePathname()
    const routes = useMemo(
        () => [
            {
                label: "Commands",
                destination: "/commands",
                isActive: pathname === "/commands"
            },
            {
                label: "Docs",
                destination: "https://docs.marly.bot",
                isActive: pathname === "https://docs.marly.bot"
            }
        ],
        [pathname]
    )

    const handleLoadingComplete = () => {
        setIsLoading(false)
    }

    if (isLoading) {
        return <Loading onComplete={handleLoadingComplete} />
    }

    return (
        <AnimatePresence>
            <div className="relative px-10 top-[30px] inset-x-0 z-[100] pb-20">
                <nav className="flex items-center justify-between w-full max-w-5xl mx-auto">
                    <div className="flex-grow basis-0">
                        <Link className="inline-flex items-center" href="/">
                            <Image
                                alt="marly logo"
                                src={marly}
                                width="500"
                                height="500"
                                decoding="async"
                                data-nimg="1"
                                className="w-12 h-12 md:w-16 md:h-16"
                                style={{ color: "transparent" }}
                            />
                            <h1 className="ml-3 text-3xl font-bold text-gradient"></h1>
                        </Link>
                    </div>
                    <div
                        className="items-center hidden py-4 px-6 sm:flex gap-x-10"
                        style={{
                            borderRadius: "1.25rem",
                            background:
                                "radial-gradient(1161.83% 494.55% at 50% 49.09%, rgb(17, 18, 18) 5.32%, rgb(28, 27, 27) 30.31%)",
                            backdropFilter: "blur(7.5px)"
                        }}>
                        <a
                            className="text-white border-transparent hover:border-marly-background-500"
                            href="/commands">
                            Commands
                        </a>
                        <a
                            className="text-white border-transparent hover:border-marly-background-500"
                            href="/status">
                            Status
                        </a>
                        <a
                            className="text-white border-transparent hover:border-marly-background-500"
                            href="https://docs.marly.bot">
                            Docs
                        </a>
                        <a
                            className="text-white border-transparent hover:border-marly-background-500"
                            href="/faq">
                            FAQ
                        </a>
                    </div>
                    <div className="flex items-center justify-end flex-grow basis-0 gap-x-5">
                        <button
                            className="hidden lg:flex items-center px-4 py-3.5 text-sm font-semibold transition duration-200 ease-linear bg-[#5865F2] hover:ring-2 hover:ring-[#5865F2] sm:px-5 rounded-full"
                            onClick={() => router.push("https://marly.bot/discord")}>
                            <FaDiscord className="inline-block w-5 h-5 sm:-ml-1" />
                            <span className="hidden text-[15px] sm:inline-block ml-3.5">
                                Discord
                            </span>
                        </button>
                    </div>
                </nav>
            </div>
        </AnimatePresence>
    )
}

export default Navbar
