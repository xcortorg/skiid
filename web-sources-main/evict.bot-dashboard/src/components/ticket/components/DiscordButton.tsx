import "@/components/ticket/styles/discord-button.css"
import { ReactElement } from "react"
import { PropsWithSlot } from "../util"
import OutboundLinkIcon from "./OutboundLinkIcon"

export type DiscordButtonProps = {
    disabled?: boolean
    image?: string
    type?: "primary" | "secondary" | "success" | "danger" | "link"
    url?: string
} & PropsWithSlot

export default function DiscordButton({
    children,
    disabled,
    image,
    type = "primary",
    url
}: DiscordButtonProps): ReactElement {
    if (type === "link" && url && !disabled) {
        return (
            <a
                className="discord-button discord-button-link"
                href={url}
                target="_blank"
                rel="noopener noreferrer">
                {image && <img className="discord-button-emoji" src={image} alt="" />}
                {children}
                <OutboundLinkIcon />
            </a>
        )
    }

    return (
        <button
            className={`discord-button discord-button-${type} ${disabled ? " discord-button-disabled" : ""}`}
            disabled={disabled}>
            {image && <img className="discord-button-emoji" src={image} alt="" />}
            {children}
            {type === "link" && <OutboundLinkIcon />}
        </button>
    )
}