"use client"
import { motion } from "framer-motion"
import Image from "next/image"

export default function Loading() {
    return (
        <div className="fixed inset-0 flex m-h-screen justify-center flex-col items-center bg-[#776dd4] z-[99]">
            <motion.div
                initial={{ opacity: 1, y: 0, scale: 0.4 }}
                animate={{ opacity: 1, y: 0, scale: [0.4, 0.6, 0.4] }}
                transition={{
                    ease: "easeInOut",
                    duration: 1.5,
                    repeat: Infinity,
                    repeatType: "loop"
                }}
                className="rounded-2xl">
                <Image
                    src={"https://r2.evict.bot/evict-new.png"}
                    alt="evict"
                    width={300}
                    height={300}
                    className="rounded-2xl"
                />
            </motion.div>
        </div>
    )
}
