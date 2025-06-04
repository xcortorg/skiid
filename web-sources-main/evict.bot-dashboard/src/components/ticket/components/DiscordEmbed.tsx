import { util } from "@/components/ticket"
import "@/components/ticket/styles/discord-embed.css"
import { ReactElement, isValidElement } from "react"
import { PropsWithSlot, elementsWithoutSlot, findSlot } from "../util"

export type DiscordEmbedProps = {
    authorIcon?: string
    authorName?: string
    authorUrl?: string
    borderColor?: string
    embedTitle?: string
    image?: string
    footerIcon?: string
    thumbnail?: string
    timestamp?: Date | string
    url?: string
}

export default function DiscordEmbed({
    authorIcon,
    authorName,
    authorUrl,
    children,
    borderColor,
    embedTitle,
    footerIcon,
    image,
    thumbnail,
    timestamp,
    url
}: DiscordEmbedProps & PropsWithSlot): ReactElement {
    const slots = {
        default: children,
        fields: findSlot(children, "fields"),
        footer: findSlot(children, "footer")
    }

    if (slots.fields) {
        if (!isValidElement(slots.fields)) {
            throw new Error(
                'Element with slot name "fields" should be a valid DiscordEmbedFields component.'
            )
        }

        slots.default = elementsWithoutSlot(slots.default, "fields")
    }

    if (slots.footer) slots.default = elementsWithoutSlot(slots.default, "footer")

    const content = {
        author: (
            <div className="discord-embed-author">
                {authorIcon && (
                    <img className="discord-embed-author-icon" src={authorIcon} alt="" />
                )}
                {authorUrl ? (
                    <a href={authorUrl} target="_blank" rel="noopener noreferrer">
                        {authorName}
                    </a>
                ) : (
                    <span>{authorName}</span>
                )}
            </div>
        ),
        footer: (
            <div className="flex items-center space-x-2 text-white">
                {slots.footer && footerIcon && <img className="w-4 h-4 rounded-lg" src={footerIcon} alt="" />}
                <span className="flex items-center space-x-1">
                    <span>{slots.footer}</span>
                    {slots.footer && timestamp && <span className="text-white">&bull;</span>}
                    {timestamp && (
                        <span>
                            {util.parseTimestamp({
                                timestamp,
                                format: "compact"
                            })}
                        </span>
                    )}
                </span>
            </div>
        ),
        title: (
            <div className="discord-embed-title">
                {url ? (
                    <a href={url} target="_blank" rel="noopener noreferrer">
                        {embedTitle}
                    </a>
                ) : (
                    <span>{embedTitle}</span>
                )}
            </div>
        )
    }

    return (
        <div className="discord-embed">
            <div
                className="discord-embed-left-border"
                style={{ backgroundColor: borderColor }}></div>
            <div className="discord-embed-container">
                <div className="discord-embed-content">
                    <div>
                        {authorName && content.author}
                        {embedTitle && content.title}
                        <div className="discord-embed-description">{slots.default}</div>
                        {slots.fields}
                        {image && <img className="discord-embed-image" src={image} alt="" />}
                    </div>
                    {thumbnail && (
                        <img className="discord-embed-thumbnail" src={thumbnail} alt="" />
                    )}
                </div>
                {(slots.footer || timestamp) && content.footer}
            </div>
        </div>
    )
}
