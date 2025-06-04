import colorToRgba from "color-rgba"
import { Children, PropsWithChildren, ReactElement, ReactNode } from "react"
export { default as markdownParser } from "./markdown"

export type PropsWithSlot = PropsWithChildren<{ slot?: string }>

export const elementsWithoutSlot = (
    elements: ReactNode | ReactNode[],
    name: string
): ReactNode | ReactNode[] => {
    return Children.map(elements as ReactElement[], (element: ReactElement): ReactNode => {
        if (element?.props?.slot === name) return
        return element
    })
}

export const findSlot = (elements: ReactNode, name: string): ReactNode => {
    return (Children.toArray(elements) as ReactElement[]).find(
        (element: ReactElement): ReactNode => {
            return element?.props?.slot === name
        }
    )
}

export const parseColorToRgba = (color?: string, alpha?: number): string | null => {
    if (!color) return null
    const [r, g, b, a] = colorToRgba(color) ?? []
    return `rgba(${r},${g},${b},${alpha ?? a})`
}

export type TimestampOptions = {
    timestamp: Date | string
    format: "compact" | "cozy"
}

export const defaultTimestamp = new Date()

export const parseTimestamp = ({ timestamp, format = "cozy" }: TimestampOptions): string => {
    if (!(timestamp instanceof Date)) timestamp = new Date(timestamp)

    if (format === "compact") {
        const [hour, minutes] = [timestamp.getHours(), timestamp.getMinutes()]
        return [
            hour > 12 ? hour - 12 : hour === 0 ? 12 : hour,
            `:${minutes.toString().padStart(2, "0")} `,
            hour >= 12 ? "PM" : "AM"
        ].join("")
    }

    const [month, day, year] = [
        timestamp.getMonth() + 1,
        timestamp.getDate(),
        timestamp.getFullYear()
    ]
    return `${month.toString().padStart(2, "0")}/${day.toString().padStart(2, "0")}/${year}`
}

export const resolveImage = (images: { [key: string]: string }, image: string): string => {
    return images[image] ?? image ?? images?.default
}
