import "@/components/ticket/styles/discord-reaction.css"
import { ReactElement } from "react"

export type DiscordReactionProps = {
    active?: boolean
    count?: number
    image: string
    name?: string
}

export default function DiscordReaction({
    active,
    count = 1,
    image,
    name
}: DiscordReactionProps): ReactElement {
    let classes = "discord-reaction"
    if (active) classes += " discord-reaction-active"

    return (
        <div className={classes} title={name}>
            <img className="discord-reaction-emoji" src={image} alt={name} />
            <span className="discord-reaction-count">{count}</span>
        </div>
    )
}
