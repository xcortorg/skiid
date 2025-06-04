"use client"

import { Gradient } from "@/components/gradient"
import "@/styles/globals.css"
import { useEffect, useState } from "react"

export function MeshGradient() {
    const [isLoaded, setIsLoaded] = useState(false)

    useEffect(() => {
        const gradient = new Gradient()
        gradient.initGradient("#gradient-canvas")

        const timer = setTimeout(() => {
            setIsLoaded(true)
        }, 100)

        return () => clearTimeout(timer)
    }, [])

    const opacity = isLoaded ? "0.4" : "0"

    return (
        <canvas
            id="gradient-canvas"
            className="absolute inset-0 w-full h-full transition-all duration-500"
            style={
                {
                    opacity
                } as React.CSSProperties
            }
            data-transition-in
        />
    )
}
