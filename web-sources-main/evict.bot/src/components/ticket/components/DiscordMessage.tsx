import { util } from "@/components/ticket"
import "@/components/ticket/styles/discord-message.css"
import { Fragment, PropsWithChildren, ReactElement, isValidElement, useContext } from "react"
import DiscordDefaultOptions, {
    DiscordMessageOptions,
    Profile
} from "../context/DiscordDefaultOptions"
import DiscordOptionsContext from "../context/DiscordOptionsContext"
import { elementsWithoutSlot, findSlot } from "../util"
import AuthorInfo from "./AuthorInfo"

export type DiscordMessageProps = PropsWithChildren<{
    author?: string
    avatar?: string
    bot?: boolean
    edited?: boolean
    profile?: string
    roleColor?: string
    timestamp?: Date | string
}>

export default function DiscordMessage({
    author,
    bot,
    children,
    compactMode,
    edited,
    profile: profileKey,
    roleColor,
    timestamp = util.defaultTimestamp
}: DiscordMessageProps & { compactMode?: boolean }): ReactElement {
    const options: DiscordMessageOptions =
        useContext(DiscordOptionsContext) ?? DiscordDefaultOptions

    const profile: Profile = !profileKey ? {} : (options.profiles?.[profileKey] ?? {})
    const user: Profile = {
        author: !author && profile?.author ? profile.author : author || "User",
        avatar: profile?.avatar,
        bot: bot ?? profile?.bot,
        roleColor: roleColor || profile?.roleColor
    }

    const messageTimestamp = util.parseTimestamp({
        timestamp,
        format: compactMode ? "compact" : "cozy"
    })

    const slots = {
        default: children,
        actions: findSlot(children, "actions"),
        embeds: findSlot(children, "embeds"),
        interactions: findSlot(children, "interactions"),
        reactions: findSlot(children, "reactions")
    }

    if (slots.actions) {
        if (!isValidElement(slots.actions)) {
            throw new Error(
                'Element with slot name "actions" should be a valid DiscordButtons component.'
            )
        }

        slots.default = elementsWithoutSlot(slots.default, "actions")
    }

    if (slots.embeds) {
        if (!isValidElement(slots.embeds)) {
            throw new Error(
                'Element with slot name "embeds" should be a valid DiscordEmbed component.'
            )
        }

        slots.default = elementsWithoutSlot(slots.default, "embeds")
    }

    if (slots.interactions) {
        if (!isValidElement(slots.interactions)) {
            throw new Error(
                'Element with slot name "interactions" should be a valid DiscordInteraction component.'
            )
        }

        slots.default = elementsWithoutSlot(slots.default, "interactions")
    }

    if (slots.reactions) {
        if (!isValidElement(slots.reactions)) {
            throw new Error(
                'Element with slot name "reactions" should be a valid DiscordEmbed component.'
            )
        }

        slots.default = elementsWithoutSlot(slots.default, "reactions")
    }

    const ephemeralMessage = (slots?.interactions as ReactElement)?.props?.ephemeral

    const highlightMessage =
        (Array.isArray(slots?.default) &&
            slots.default.some(
                element =>
                    isValidElement(element) &&
                    // This prolly wont error
                    // @ts-ignore
                    element.props?.highlight &&
                    // @ts-ignore
                    element.props?.type !== "channel"
            )) ||
        (isValidElement(slots?.interactions) && slots.interactions.props?.highlight)

    let messageClasses = "discord-message"
    if (ephemeralMessage) messageClasses += " discord-ephemeral-highlight"
    if (highlightMessage && !ephemeralMessage) messageClasses += " discord-mention-highlight"

    return (
        <div className={messageClasses}>
            {slots.interactions}
            <div className="discord-message-content">
                <div className="discord-author-avatar">
                    <img
                        src={user.avatar ?? "https://cdn.discordapp.com/embed/avatars/0.png"}
                        alt=""
                    />
                </div>
                <div className="discord-message-body">
                    {!compactMode ? (
                        <div>
                            <AuthorInfo
                                author={user.author}
                                bot={user.bot}
                                roleColor={user.roleColor}
                            />
                            <span className="discord-message-timestamp">{messageTimestamp}</span>
                        </div>
                    ) : (
                        <Fragment>
                            <span className="discord-message-timestamp">{messageTimestamp}</span>
                            <AuthorInfo
                                author={user.author}
                                bot={user.bot}
                                roleColor={user.roleColor}
                            />
                        </Fragment>
                    )}
                    {slots.default}
                    {edited && <span className="discord-message-edited">(edited)</span>}
                    {slots.embeds}
                    {slots.actions}
                    {ephemeralMessage && (
                        <div className="discord-message-ephemeral-notice">
                            Only you can see this
                        </div>
                    )}
                    {slots.reactions}
                </div>
            </div>
        </div>
    )
}
