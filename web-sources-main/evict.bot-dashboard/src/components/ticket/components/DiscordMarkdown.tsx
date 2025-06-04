import { util } from "@/components/ticket"
import "@/components/ticket/styles/discord-markdown.css"
import { Children, Fragment, ReactElement, ReactNode } from "react"
import DiscordChannelMention from "./DiscordChannelMention"
import DiscordMention from "./DiscordMention"

export default function DiscordMarkdown({ children }: { children?: ReactNode }): ReactElement {
    const parsedContent = Children.map(children, (child: ReactNode): ReactNode => {
        if (typeof child !== "string" || !child.length) return child

        let text = child.toString()
        const parts: (string | ReactElement)[] = []
        let lastIndex = 0

        const regex = /<[#@](\d+)>/g
        let match

        while ((match = regex.exec(text)) !== null) {
            if (match.index > lastIndex) {
                parts.push(text.slice(lastIndex, match.index))
            }

            if (match[0].startsWith('<#')) {
                parts.push(<DiscordChannelMention key={match.index} channel={`channel-${match[1].slice(-4)}`} />)
            } else {
                parts.push(<DiscordMention key={match.index}>{match[1]}</DiscordMention>)
            }

            lastIndex = match.index + match[0].length
        }

        if (lastIndex < text.length) {
            parts.push(text.slice(lastIndex))
        }

        return parts.map((part, index) => {
            if (typeof part === 'string') {
                return (
                    <span
                        key={index}
                        className="discord-markdown-content"
                        dangerouslySetInnerHTML={{
                            __html: util.markdownParser.toHTML(part)
                        }}
                    />
                )
            }
            return part
        })
    })

    return <span className="discord-markdown">{parsedContent}</span>
}