import "@/components/ticket/styles/discord-embed-field.css"
import { PropsWithChildren, ReactElement } from "react"

export type DiscordEmbedFieldProps = PropsWithChildren<{
    inline?: boolean
    fieldTitle: string
    text: string
}>

export default function DiscordEmbedField({
    text,
    inline,
    fieldTitle
}: DiscordEmbedFieldProps): ReactElement {
    let classes = "discord-embed-field"
    if (inline) classes += " discord-embed-field-inline"

    return (
        <div className={classes}>
            <div className="discord-embed-field-title">{fieldTitle}</div>
            {text}
        </div>
    )
}
