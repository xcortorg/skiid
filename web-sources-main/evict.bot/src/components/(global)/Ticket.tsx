"use client"

import Loader from "@/components/(global)/Loader"
import {
    DiscordButton,
    DiscordButtons,
    DiscordEmbed,
    DiscordEmbedField,
    DiscordEmbedFields,
    DiscordMarkdown,
    DiscordMention,
    DiscordMessage,
    DiscordMessages,
    DiscordOptionsContext,
    DiscordReaction,
    DiscordReactions
} from "@/components/ticket"
import { useRouter } from "next/navigation"
import React, { useEffect, useState } from "react"

interface TicketMention {
    message_id: number
    user_id: number
}

interface TicketAttachment {
    file_size: number
    filename: string
    message_id: number
    url: string
}

interface TicketMessage {
    id: number
    author_id: number
    channel_id: number
    content: string
    created_at: string
    edited_timestamp: string | null
    pinned: boolean
    timestamp: string
    mentions: TicketMention[]
}

interface TicketEmbed {
    title: string
    description: string
    url: string
    color: number
    message_id: number
    author?: {
        name: string
        icon_url: string
        url: string
    }
    footer?: {
        text: string
        icon_url: string
    }
    timestamp?: string
    thumbnail?: {
        url: string
    }
    image?: {
        url: string
    }
    fields?: {
        name: string
        value: string
        inline: boolean
    }[]
}

interface UserProfile {
    accent_color: null | number
    author_id: number
    avatar: string
    banner: null | string
    bot: boolean
    channel_id: number
    content: string
    created_at: string
    discriminator: string
    edited_timestamp: null | string
    global_name: null | string
    id: number
    mfa_enabled: boolean
    pinned: boolean
    system: boolean
    timestamp: string
    username: string
}

interface Channel {
    created_at: string
    id: string
    name: string
    type: string
}

interface TicketReaction {
    message_id: number
    emoji: string
    count: number
    url: string
    active: boolean
}

interface TicketButton {
    message_id: number
    label: string
    style: string
    custom_id?: string
    url?: string
    disabled: boolean
    image: string
}

interface InternalIds {
    ids: number[]
}

interface Ids {
    internalIds: InternalIds
}

interface TicketData {
    channel: Channel
    embeds: TicketEmbed[]
    mentions: TicketMention[]
    messages: TicketMessage[]
    reactions: TicketReaction[]
    buttons: TicketButton[]
    ticket: {
        channel_id: number
        closed_at: string
        closed_by_id: number
        guild_id: number
        opened_by_id: number
        reason: string
    }
    users: UserProfile[]
    attachments: TicketAttachment[]
}

interface PageProps {
    session: any
    params: {
        ticketId: string
    }
}

const TicketTranscriptPage: React.FC<PageProps> = ({ session, params }) => {
    const [data, setData] = useState<TicketData | null>(null)
    const [ids, setIds] = useState<Ids | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<Error | null>(null)
    const router = useRouter()

    useEffect(() => {
        const fetchData = async () => {
            if (!session?.user?.id) {
                const currentPath = window.location.pathname
                router.push(`/login?redirect=${encodeURIComponent(currentPath)}`)
                return
            }

            try {
                const response = await fetch(`/api/tickets?id=${params.ticketId}`)
                if (!response.ok) {
                    if (response.status === 403) {
                        throw new Error("You are not allowed to view this ticket")
                    }
                    throw new Error("This ticket was not found.")
                }
                const jsonData = await response.json()
                setData(jsonData)
            } catch (err) {
                // Logging COMPLETELY disabled for production.
                // console.error("Error fetching data:", err)
                setError(err instanceof Error ? err : new Error("An unknown error occurred"))
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [params.ticketId, session])

    const [messages, setMessages] = useState<TicketMessage[]>([])
    const [users, setUsers] = useState<UserProfile[]>([])

    useEffect(() => {
        if (data) {
            setMessages(data.messages)
            setUsers(data.users)
        }
    }, [data])

    if (loading) return <Loader />
    if (error)
        return (
            <div className="flex items-center justify-center text-white">
                <p className="text-2xl px-4">Error: {error.message}</p>
            </div>
        )

    if (data?.channel?.name === undefined)
        return (
            <main className="flex items-center justify-center flex-col pb-20 pt-20">
                <div className="flex flex-col mx-10 items-center text-center justify-center sm:mx-0">
                    <h1 className="text-[12rem] pb-6">😔</h1>
                    <h1 className="text-white font-normal text-4xl sm:text-6xl">
                        No Messages In Ticket
                    </h1>
                </div>
            </main>
        )

    const replaceMentions = (content: string) => {
        const urlRegex = /(https?:\/\/[^\s]+)/g
        const parts = content.split(urlRegex)
        return parts.map((part, index) => {
            if (index % 2 === 1) {
                return (
                    <div key={`url-${index}`} className="url-preview">
                        <a href={part} target="_blank" rel="noopener noreferrer">
                            {part}
                        </a>
                    </div>
                )
            }

            const mentionRegex = /<@!?(\d+)>/g
            const mentionParts = part.split(mentionRegex)
            return mentionParts.map((mentionPart, mentionIndex) => {
                if (mentionIndex % 2 === 1) {
                    const userId = mentionPart
                    const user = users.find(user => user.id === Number(userId))
                    if (user) {
                        return <DiscordMention key={userId} profile={user.id.toString()} />
                    } else {
                        return `@${userId}`
                    }
                } else {
                    return mentionPart
                }
            })
        })
    }

    return (
        <div className="2xl:container 2xl:mx-auto px-5 pb-10 md:px-[8vw] 2xl:px-52 2xl:py-4">
            <h1 className="font-bold text-4xl">#{data?.channel.name}</h1>
            <h1 className="font-medium text-md text-evict-secondary">
                Closure Reason: {data?.ticket.reason ?? "No Reason Provided"}
            </h1>
            <DiscordOptionsContext.Provider
                value={{
                    profiles: generateProfiles(users),
                    avatars: {
                        blue: "",
                        gray: "",
                        green: "",
                        orange: "",
                        red: ""
                    },
                    defaultMode: "cozy",
                    defaultTheme: "dark"
                }}>
                <DiscordMessages>
                    {messages.map(msg => {
                        const author = users.find(user => user.id === msg.author_id)
                        const replacedContent = replaceMentions(msg.content).flat()
                        const attachments: TicketAttachment[] | undefined =
                            data?.attachments.filter(
                                (attachment: TicketAttachment) => attachment.message_id === msg.id
                            )

                        const embed = data?.embeds?.find(e => e.message_id === msg.id)
                        const reactions = data?.reactions.filter(r => r.message_id === msg.id) || []
                        const buttons = data?.buttons?.filter(b => b.message_id === msg.id) || []

                        return (
                            <DiscordMessage
                                key={msg.id.toString()}
                                profile={author?.id.toString()}
                                author={`${author?.global_name ?? author?.username} (${author?.username})`}
                                avatar={author?.avatar}
                                timestamp={msg.timestamp}
                                edited={msg.edited_timestamp !== null}
                                bot={author?.bot}>
                                <DiscordMarkdown>{replacedContent} </DiscordMarkdown>
                                {attachments?.map((attachment: TicketAttachment) => {
                                    if (
                                        attachment.filename.endsWith(".jpg") ||
                                        attachment.filename.endsWith(".jpeg") ||
                                        attachment.filename.endsWith(".png")
                                    ) {
                                        return (
                                            <div key={attachment.url}>
                                                <img
                                                    src={attachment.url}
                                                    alt={attachment.filename}
                                                />
                                            </div>
                                        )
                                    } else if (
                                        attachment.filename.endsWith(".mp4") ||
                                        attachment.filename.endsWith(".mov") ||
                                        attachment.filename.endsWith(".avi")
                                    ) {
                                        return (
                                            <div key={attachment.url} className="my-2">
                                                <video
                                                    controls
                                                    className="h-[50vh] m-w-[50vw] rounded-lg">
                                                    <source src={attachment.url} type="video/mp4" />
                                                    Your browser does not support the video tag.
                                                </video>
                                            </div>
                                        )
                                    } else {
                                        return (
                                            <div key={attachment.url}>
                                                Attachment{" "}
                                                <a
                                                    href={attachment.url}
                                                    target="_blank"
                                                    rel="noopener noreferrer">
                                                    {attachment.filename}
                                                </a>
                                            </div>
                                        )
                                    }
                                })}
                                {embed && (
                                    <DiscordEmbed
                                        slot="embeds"
                                        authorIcon={embed.author?.icon_url}
                                        authorName={embed.author?.name}
                                        authorUrl={embed.author?.url}
                                        borderColor={`#${embed.color.toString(16).padStart(6, "0")}`}
                                        embedTitle={embed.title}
                                        url={embed.url}
                                        image={embed.image?.url}
                                        footerIcon={embed.footer?.icon_url}
                                        thumbnail={embed.thumbnail?.url}
                                        timestamp={embed.timestamp}>
                                        <DiscordMarkdown>{embed.description}</DiscordMarkdown>
                                        {embed.footer && (
                                            <div slot="footer">{embed.footer.text}</div>
                                        )}
                                        {embed.fields && (
                                            <DiscordEmbedFields>
                                                {embed.fields.map((field, index) => (
                                                    <DiscordEmbedField
                                                        key={index}
                                                        fieldTitle={field.name}
                                                        inline={field.inline}
                                                        text={field.value}
                                                    />
                                                ))}
                                            </DiscordEmbedFields>
                                        )}
                                    </DiscordEmbed>
                                )}
                                {reactions && reactions.length > 0 && (
                                    <DiscordReactions>
                                        {reactions.map((reaction, index) => (
                                            <DiscordReaction
                                                key={index}
                                                name={reaction.emoji}
                                                count={reaction.count}
                                                image={reaction.url}
                                                active={reaction.active}
                                            />
                                        ))}
                                    </DiscordReactions>
                                )}
                                {buttons && buttons.length > 0 && (
                                    <DiscordButtons>
                                        {buttons.map((button, index) => (
                                            <DiscordButton
                                                key={index}
                                                type={
                                                    button.style as
                                                        | "link"
                                                        | "primary"
                                                        | "secondary"
                                                        | "success"
                                                        | "danger"
                                                        | undefined
                                                }
                                                url={button.url}
                                                disabled={button.disabled}
                                                image={button.image}>
                                                {button.label}
                                            </DiscordButton>
                                        ))}
                                    </DiscordButtons>
                                )}
                            </DiscordMessage>
                        )
                    })}
                </DiscordMessages>
            </DiscordOptionsContext.Provider>
        </div>
    )
}

export default TicketTranscriptPage

function generateProfiles(
    users: UserProfile[]
): Record<string, { author: string; avatar: string; roleColor: string }> {
    return users.reduce(
        (acc, user) => {
            acc[user.id.toString()] = {
                author: user.global_name ?? user.username,
                avatar: user.avatar,
                roleColor: "#fffff" // Placeholder for role color
            }
            return acc
        },
        {} as Record<string, { author: string; avatar: string; roleColor: string }>
    )
}
