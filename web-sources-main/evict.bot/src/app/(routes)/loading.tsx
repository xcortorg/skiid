"use client"
import { AnimatePresence, motion } from "framer-motion"
import Image from "next/image"
import { useEffect, useState } from "react"

export default function Loading() {
    const [isVisible, setIsVisible] = useState(true)
    const [showLoader, setShowLoader] = useState(true)

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsVisible(false)
        }, 1500)
        return () => clearTimeout(timer)
    }, [])

    if (!showLoader) return null

    return (
        <AnimatePresence onExitComplete={() => setShowLoader(false)} mode="wait">
            {isVisible && (
                <motion.div
                    key="loader"
                    className="fixed inset-0 flex min-h-screen justify-center items-center bg-[#0A0A0B]/95 backdrop-blur-md z-[99]"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{
                        opacity: 0,
                        transition: {
                            duration: 1.5,
                            ease: [0.22, 1, 0.36, 1],
                            delay: 0.1
                        }
                    }}>
                    <div className="flex flex-col items-center gap-8">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9, filter: "blur(5px)" }}
                            animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                            exit={{
                                opacity: 0,
                                scale: 0.95,
                                filter: "blur(5px)",
                                transition: {
                                    duration: 0.8,
                                    ease: [0.22, 1, 0.36, 1]
                                }
                            }}>
                            <Image
                                src="https://r2.evict.bot/evict-new.png"
                                alt="evict"
                                width={120}
                                height={120}
                                className="rounded-3xl drop-shadow-[0_0_25px_rgba(255,255,255,0.1)] brightness-100 [filter:_brightness(1)_sepia(0.1)_saturate(1.65)_hue-rotate(220deg)]"
                                priority
                            />
                        </motion.div>

                        <motion.div
                            className="flex gap-2"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{
                                opacity: 0,
                                y: 10,
                                transition: {
                                    duration: 0.7,
                                    ease: [0.22, 1, 0.36, 1]
                                }
                            }}>
                            {[...Array(3)].map((_, i) => (
                                <motion.div
                                    key={i}
                                    className="w-2.5 h-2.5 rounded-full bg-white/10"
                                    animate={{
                                        scale: isVisible ? [1, 1.2, 1] : 1,
                                        opacity: isVisible ? [0.3, 1, 0.3] : 0.1
                                    }}
                                    exit={{
                                        scale: 0,
                                        opacity: 0,
                                        transition: {
                                            duration: 0.5,
                                            delay: i * 0.1
                                        }
                                    }}
                                    transition={{
                                        duration: 1.2,
                                        repeat: isVisible ? Infinity : 0,
                                        delay: i * 0.15,
                                        ease: [0.25, 0.1, 0, 1]
                                    }}
                                />
                            ))}
                        </motion.div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    )
}
