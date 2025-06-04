import { util } from "@/components/ticket"
import "@/components/ticket/styles/discord-mention.css"
import React, {
    PropsWithChildren,
    ReactElement,
    useContext,
    useEffect,
    useRef,
    useState
} from "react"
import DiscordDefaultOptions, {
    DiscordMessageOptions,
    Profile
} from "../context/DiscordDefaultOptions"
import DiscordOptionsContext from "../context/DiscordOptionsContext"

export type DiscordMentionProps = PropsWithChildren<{
    highlight?: boolean
    profile?: string
    roleColor?: string
    type?: string
}>

export default function DiscordMention({
    children,
    roleColor,
    profile: profileKey,
    type = "user"
}: DiscordMentionProps): ReactElement {
    const options: DiscordMessageOptions =
        useContext(DiscordOptionsContext) ?? DiscordDefaultOptions
    const root = useRef<HTMLSpanElement>(null)
    const profile: Profile = !profileKey ? {} : (options.profiles?.[profileKey] ?? {})
    const color = roleColor ?? profile?.roleColor

    const [hovering, setHovering] = useState(false)
    const setHoverColor = () => setHovering(true)
    const resetHoverColor = () => setHovering(false)

    const colors = {
        background: util.parseColorToRgba(color, 0.1),
        hover: util.parseColorToRgba(color, 0.3)
    }

    const colorStyle: React.CSSProperties | undefined =
        color && type === "role"
            ? ({
                  color,
                  backgroundColor: hovering ? colors.hover : colors.background || undefined
              } as React.CSSProperties)
            : undefined

    useEffect(() => {
        if (color && type === "role") {
            root?.current?.addEventListener("mouseenter", setHoverColor)
            root?.current?.addEventListener("mouseout", resetHoverColor)
        }

        return () => {
            root?.current?.removeEventListener("mouseenter", setHoverColor)
            root?.current?.removeEventListener("mouseout", resetHoverColor)
        }
    }, [root, color, type])

    const defaultContent =
        children && children !== ""
            ? children
            : type === "user" && profile?.author
              ? profile.author
              : type === "channel"
                ? type
                : type.charAt(0).toUpperCase() + type.slice(1)

    const mentionCharacter = type === "channel" ? "#" : "@"

    return (
        <span ref={root} className="discord-mention" style={colorStyle}>
            {mentionCharacter}
            {defaultContent}
        </span>
    )
}
