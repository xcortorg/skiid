import "@/components/ticket/styles/discord-author-info.css"
import { ReactElement } from "react"

type AuthorInfoProps = {
    author?: string
    bot?: boolean
    roleColor?: string
}

export default function AuthorInfo({
    author,
    bot,
    className,
    roleColor
}: AuthorInfoProps & { className?: string }): ReactElement {
    let authorInfoClasses = "discord-author-info"
    if (className) authorInfoClasses += ` ${className}`

    return (
        <span className={authorInfoClasses}>
            <span className="discord-author-username" style={{ color: roleColor }}>
                {author}
            </span>
            {bot && <span className="discord-author-bot-tag">Bot</span>}
        </span>
    )
}
