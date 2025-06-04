"use client"

import { cn } from "@/libs/util"

interface HeadingProps {
    size?: "xl" | "lg"
    color?: "gray" | "white"
    weight?: "semibold" | "bold"
    children?: React.ReactNode
    className?: string
}

const Heading: React.FC<HeadingProps> = ({ size, color, weight, children, className }) => {
    return (
        <h1
            className={cn(
                `${weight === "bold" ? "font-bold" : "font-semibold"} tracking-tight ${
                    size === "xl" ? "text-7xl" : "text-3xl"
                } ${color === "gray" ? "text-zinc-400" : "text-white"}`,
                className
            )}>
            {children}
        </h1>
    )
}

export default Heading
