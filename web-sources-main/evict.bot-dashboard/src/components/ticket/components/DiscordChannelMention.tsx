import { ReactElement } from "react"

interface DiscordChannelMentionProps {
    channel?: string
}

export default function DiscordChannelMention({ channel = "channel" }: DiscordChannelMentionProps): ReactElement {
    return (
        <span className="inline-flex items-center text-[#949cf7] bg-[#949cf726] rounded px-[0.3rem] font-medium cursor-pointer hover:bg-[#949cf733]">
            <span className="mr-[0.1rem]">#</span>
            {channel}
        </span>
    )
} 