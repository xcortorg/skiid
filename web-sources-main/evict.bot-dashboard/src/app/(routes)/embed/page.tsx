"use client"

import DiscordButton from "@/components/ticket/components/DiscordButton"
import DiscordButtons from "@/components/ticket/components/DiscordButtons"
import DiscordEmbed from "@/components/ticket/components/DiscordEmbed"
import DiscordEmbedField from "@/components/ticket/components/DiscordEmbedField"
import DiscordEmbedFields from "@/components/ticket/components/DiscordEmbedFields"
import DiscordMarkdown from "@/components/ticket/components/DiscordMarkdown"
import DiscordMessage from "@/components/ticket/components/DiscordMessage"
import DiscordMessages from "@/components/ticket/components/DiscordMessages"
import DiscordDefaultOptions from "@/components/ticket/context/DiscordDefaultOptions"
import DiscordOptionsContext from "@/components/ticket/context/DiscordOptionsContext"
import { motion } from "framer-motion"
import { Info, Save } from "lucide-react"
import { useState } from "react"

interface EmbedState {
    color: string
    title?: string
    description?: string
    timestamp?: boolean
    url?: string
    author?: {
        name?: string
        icon_url?: string
        url?: string
    }
    image?: string
    thumbnail?: string
    footer?: {
        text?: string
        icon_url?: string
    }
    fields?: Array<{
        name: string
        value: string
        inline: boolean
    }>
    content?: string
    buttons?: Array<{
        label?: string
        url?: string
        emoji?: string
        style: "red" | "green" | "gray" | "blue"
        disabled: boolean
    }>
    delete_after?: number
}

const DISCORD_LIMITS = {
    TITLE: 256,
    DESCRIPTION: 4096,
    FIELD_NAME: 256,
    FIELD_VALUE: 1024,
    FOOTER_TEXT: 2048,
    AUTHOR_NAME: 256,
    FIELDS: 25,
    BUTTONS: 5
}

function generateScript(embed: EmbedState): string {
    let script = ""

    if (embed.content) script += `{content: ${embed.content}}$v`

    const hasEmbedProperties =
        embed.title ||
        embed.description ||
        embed.timestamp ||
        embed.author?.name ||
        embed.author?.icon_url ||
        embed.thumbnail ||
        embed.image ||
        embed.footer?.text ||
        embed.footer?.icon_url ||
        (embed.fields && embed.fields.length > 0) ||
        embed.color !== "#000000"

    if (hasEmbedProperties) {
        script += `{embed}{color: ${embed.color}}`

        if (embed.title) script += `$v{title: ${embed.title}}`
        if (embed.description) script += `$v{description: ${embed.description}}`
        if (embed.timestamp) script += `$v{timestamp}`
        if (embed.author?.name || embed.author?.icon_url) {
            script += `$v{author: `
            if (embed.author.name) script += `name: ${embed.author.name}`
            if (embed.author.icon_url) {
                if (embed.author.name) script += " && "
                script += `icon: ${embed.author.icon_url}`
            }
            script += `}`
        }
        if (embed.thumbnail) script += `$v{thumbnail: ${embed.thumbnail}}`
        if (embed.image) script += `$v{image: ${embed.image}}`
        if (embed.footer?.text || embed.footer?.icon_url) {
            script += `$v{footer: `
            if (embed.footer.text) script += `text: ${embed.footer.text}`
            if (embed.footer.icon_url) {
                if (embed.footer.text) script += " && "
                script += `icon: ${embed.footer.icon_url}`
            }
            script += `}`
        }

        if (embed.buttons?.length) {
            embed.buttons.forEach(button => {
                script += `$v{button: `
                if (button.label) script += `label: ${button.label}`
                if (button.url) {
                    if (button.label) script += " && "
                    script += `url: ${button.url}`
                }
                if (button.emoji) {
                    if (button.label || button.url) script += " && "
                    script += `emoji: ${button.emoji}`
                }
                if (button.style !== "gray") {
                    if (button.label || button.url || button.emoji) script += " && "
                    script += `style: ${button.style}`
                }
                if (button.disabled) {
                    if (button.label || button.url || button.emoji || button.style !== "gray")
                        script += " && "
                    script += "disabled"
                }
                script += `}`
            })
        }

        if (
            embed.fields &&
            embed.fields.length > 0 &&
            embed.fields.some(field => field.name || field.value)
        ) {
            script += `$v{fields: `
            embed.fields.forEach((field, index) => {
                if (field.name || field.value) {
                    script += `name: ${field.name} && value: ${field.value} && inline: ${field.inline}`
                    if (index < (embed.fields?.length || 0) - 1) script += " && "
                }
            })
            script += `}`
        }
    }

    return script
}

const replaceVariables = (text: string) => {
    if (!text) return text

    const replacements = {
        "{guild.name}": "My Discord Server",
        "{guild.icon}": "https://r2.evict.bot/evict-new.png",
        "{guild.created_at}": "2023-08-01",
        "{guild.count}": "1,604",
        "{guild.boost_count}": "34",
        "{guild.booster_count}": "10",
        "{guild.vanity}": "evict",
        "{guild.boost_tier}": "Level 2",
        "{guild.count.format}": "1,500th",
        "{guild.boost_count.format}": "25th",
        "{guild.booster_count.format}": "10th",
        "{user}": "x14c#0",
        "{user.name}": "x14c",
        "{user.discriminator}": "#0",
        "{user.id}": "123456789012345678",
        "{user.mention}": "@x14c",
        "{user.avatar}": "https://example.com/avatar.png",
        "{user.created_at}": "2020-05-01",
        "{user.joined_at}": "2021-06-15"
    }

    let replacedText = text
    for (const [key, value] of Object.entries(replacements)) {
        replacedText = replacedText.replace(
            new RegExp(key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g"),
            value
        )
    }
    return replacedText
}

export default function EmbedPage() {
    const [embed, setEmbed] = useState<EmbedState>({
        color: "#000000",
        fields: []
    })
    const [showImportModal, setShowImportModal] = useState(false)
    const [importScript, setImportScript] = useState("")

    const updateEmbed = (updates: Partial<EmbedState>) => {
        setEmbed(prev => {
            const newEmbed = { ...prev, ...updates }

            if (newEmbed.title && newEmbed.title.length > DISCORD_LIMITS.TITLE) {
                newEmbed.title = newEmbed.title.slice(0, DISCORD_LIMITS.TITLE)
            }

            if (newEmbed.description && newEmbed.description.length > DISCORD_LIMITS.DESCRIPTION) {
                newEmbed.description = newEmbed.description.slice(0, DISCORD_LIMITS.DESCRIPTION)
            }

            if (newEmbed.author?.name && newEmbed.author.name.length > DISCORD_LIMITS.AUTHOR_NAME) {
                newEmbed.author.name = newEmbed.author.name.slice(0, DISCORD_LIMITS.AUTHOR_NAME)
            }

            if (newEmbed.footer?.text && newEmbed.footer.text.length > DISCORD_LIMITS.FOOTER_TEXT) {
                newEmbed.footer.text = newEmbed.footer.text.slice(0, DISCORD_LIMITS.FOOTER_TEXT)
            }

            if (newEmbed.fields) {
                newEmbed.fields = newEmbed.fields.slice(0, DISCORD_LIMITS.FIELDS).map(field => ({
                    ...field,
                    name: field.name.slice(0, DISCORD_LIMITS.FIELD_NAME),
                    value: field.value.slice(0, DISCORD_LIMITS.FIELD_VALUE)
                }))
            }

            if (newEmbed.buttons) {
                newEmbed.buttons = newEmbed.buttons.slice(0, DISCORD_LIMITS.BUTTONS)
            }

            return newEmbed
        })
    }

    const getButtonStyle = (
        style: "red" | "green" | "gray" | "blue"
    ): "primary" | "secondary" | "success" | "danger" | "link" => {
        switch (style) {
            case "blue":
                return "primary"
            case "gray":
                return "secondary"
            case "green":
                return "success"
            case "red":
                return "danger"
            default:
                return "secondary"
        }
    }

    const processText = (text: string) => {
        return text.split("\n").map((line, i) => (
            <DiscordMarkdown key={i}>
                {line}
                {i !== text.split("\n").length - 1 && "\n"}
            </DiscordMarkdown>
        ))
    }

    const discordOptions = {
        ...DiscordDefaultOptions,
        profiles: {
            evict: {
                avatar: "https://r2.evict.bot/evict-new.png"
            }
        }
    }

    const parseScript = (script: string) => {
        try {
            const newEmbed: EmbedState = {
                color: "#000000",
                fields: []
            }

            const contentMatch = script.match(/\{content: (.*?)\}\$v/)
            if (contentMatch) newEmbed.content = contentMatch[1]

            if (!script.includes("{embed}")) {
                throw new Error("Invalid embed script")
            }

            const colorMatch = script.match(/\{color: ([A-Fa-f0-9]{6})\}/)
            if (colorMatch) newEmbed.color = `#${colorMatch[1]}`

            const descMatch = script.match(/\$v\{description: (.*?)\}/)
            if (descMatch) newEmbed.description = descMatch[1]

            const titleMatch = script.match(/\$v\{title: (.*?)\}/)
            if (titleMatch) newEmbed.title = titleMatch[1]

            if (script.includes("$v{timestamp}")) newEmbed.timestamp = true

            if (script.includes("$v{author:")) {
                const authorMatch = script.match(/\$v\{author: (.+?)\}/)
                if (authorMatch) {
                    const authorParts = authorMatch[1].split(" && ")
                    newEmbed.author = {
                        name: authorParts
                            .find(part => part.startsWith("name: "))
                            ?.split("name: ")[1],
                        icon_url: authorParts
                            .find(part => part.startsWith("icon: "))
                            ?.split("icon: ")[1],
                        url: authorParts.find(part => part.startsWith("url: "))?.split("url: ")[1]
                    }
                }
            }

            if (script.includes("$v{thumbnail:")) {
                const thumbnailMatch = script.match(/\$v\{thumbnail: (.+?)\}/)
                if (thumbnailMatch) newEmbed.thumbnail = thumbnailMatch[1]
            }

            if (script.includes("$v{image:")) {
                const imageMatch = script.match(/\$v\{image: (.+?)\}/)
                if (imageMatch) newEmbed.image = imageMatch[1]
            }

            if (script.includes("$v{footer:")) {
                const footerMatch = script.match(/\$v\{footer: (.+?)\}/)
                if (footerMatch) {
                    const footerParts = footerMatch[1].split(" && ")
                    newEmbed.footer = {
                        text: footerParts
                            .find(part => part.startsWith("text: "))
                            ?.split("text: ")[1],
                        icon_url: footerParts
                            .find(part => part.startsWith("icon: "))
                            ?.split("icon: ")[1]
                    }
                }
            }

            if (script.includes("$v{button:")) {
                const buttonMatches = script.match(/\$v\{button: (.+?)\}/g)
                if (buttonMatches) {
                    newEmbed.buttons = buttonMatches.map(match => {
                        const buttonParts = match[1].split(" && ")
                        return {
                            label: buttonParts
                                .find(part => part.startsWith("label: "))
                                ?.split("label: ")[1],
                            url: buttonParts
                                .find(part => part.startsWith("url: "))
                                ?.split("url: ")[1],
                            emoji: buttonParts
                                .find(part => part.startsWith("emoji: "))
                                ?.split("emoji: ")[1],
                            style: buttonParts
                                .find(part => part.startsWith("style: "))
                                ?.split("style: ")[1] as "red" | "green" | "gray" | "blue",
                            disabled: buttonParts.includes("disabled")
                        }
                    })
                }
            }

            if (script.includes("$v{fields:")) {
                const fieldMatches = script.match(/\$v\{fields: (.+?)\}/g)
                if (fieldMatches) {
                    newEmbed.fields = fieldMatches.map(match => {
                        const matchResult = match.match(/\$v\{fields: (.*?)\}/)
                        if (!matchResult) return { name: "", value: "", inline: false }

                        const fieldParts = matchResult[1].split(" && ")
                        return {
                            name:
                                fieldParts
                                    .find(part => part.startsWith("name: "))
                                    ?.split("name: ")[1] || "",
                            value:
                                fieldParts
                                    .find(part => part.startsWith("value: "))
                                    ?.split("value: ")[1] || "",
                            inline: fieldParts.includes("inline")
                        }
                    })
                }
            }

            setEmbed(newEmbed)
        } catch (error) {
            console.error("Failed to parse script:", error)
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-b from-[#0A0A0B] to-black">
            <div className="relative border-b border-white/5">
                <div className="absolute inset-0 bg-[url('/noise.png')] opacity-5" />
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 md:py-12 relative">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8 }}
                        className="text-center">
                        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 md:mb-6">
                            <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-300">
                                Embed Builder
                            </span>
                        </h1>
                        <p className="text-base sm:text-lg text-gray-400 max-w-3xl mx-auto px-4">
                            Create beautiful embeds for your server with our visual builder
                        </p>
                    </motion.div>
                </div>
            </div>

            <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
                <div className="space-y-6">
                    <div className="flex items-center gap-3 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl text-sm text-blue-200">
                        <Info className="w-5 h-5 flex-shrink-0" />
                        <p>
                            Variables can be used in any text field. Check out our{" "}
                            <a
                                href="https://docs.evict.bot/overview/variables"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="underline hover:text-blue-100">
                                variables documentation
                            </a>{" "}
                            to learn more.
                        </p>
                    </div>

                    <div className="w-full bg-[#313338] rounded-xl p-4">
                        <DiscordOptionsContext.Provider value={discordOptions}>
                            <DiscordMessages>
                                <DiscordMessage author="evict" bot={true} profile="evict">
                                    {embed.content && (
                                        <DiscordMarkdown>
                                            {replaceVariables(embed.content)}
                                        </DiscordMarkdown>
                                    )}
                                    <DiscordEmbed
                                        embedTitle={embed.title}
                                        authorName={embed.author?.name}
                                        authorIcon={embed.author?.icon_url}
                                        image={embed.image}
                                        thumbnail={embed.thumbnail}
                                        borderColor={embed.color}
                                        timestamp={embed.timestamp ? new Date() : undefined}
                                        footerIcon={embed.footer?.icon_url}>
                                        {embed.description && processText(embed.description)}
                                        {embed.fields && embed.fields.length > 0 && (
                                            <div slot="fields">
                                                <DiscordEmbedFields>
                                                    {embed.fields.map((field, index) => (
                                                        <DiscordEmbedField
                                                            key={index}
                                                            fieldTitle={field.name}
                                                            text={field.value}
                                                            inline={field.inline}
                                                        />
                                                    ))}
                                                </DiscordEmbedFields>
                                            </div>
                                        )}
                                        {embed.footer?.text && (
                                            <div slot="footer">
                                                <DiscordMarkdown>
                                                    {embed.footer.text}
                                                </DiscordMarkdown>
                                            </div>
                                        )}
                                    </DiscordEmbed>
                                    {embed.buttons && embed.buttons.length > 0 && (
                                        <DiscordButtons>
                                            {embed.buttons.map((button, index) => {
                                                const isUnicodeEmoji =
                                                    button.emoji &&
                                                    /\p{Extended_Pictographic}/u.test(button.emoji)

                                                return (
                                                    <DiscordButton
                                                        key={index}
                                                        type={getButtonStyle(button.style)}
                                                        disabled={button.disabled}
                                                        url={button.url}
                                                        image={
                                                            !isUnicodeEmoji
                                                                ? button.emoji
                                                                : undefined
                                                        }>
                                                        {isUnicodeEmoji
                                                            ? `${button.emoji} ${button.label}`
                                                            : button.label}
                                                    </DiscordButton>
                                                )
                                            })}
                                        </DiscordButtons>
                                    )}
                                </DiscordMessage>
                            </DiscordMessages>
                        </DiscordOptionsContext.Provider>
                    </div>

                    <div className="w-full bg-[#0A0A0B] border border-white/5 rounded-xl p-4">
                        <div className="flex items-center justify-between mb-2">
                            <h3 className="text-sm font-medium">Generated Script</h3>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setShowImportModal(true)}
                                    className="text-xs text-white/60 hover:text-white/80 transition-colors">
                                    Import
                                </button>
                                <button
                                    onClick={() =>
                                        navigator.clipboard.writeText(generateScript(embed))
                                    }
                                    className="text-xs text-white/60 hover:text-white/80 transition-colors">
                                    Copy
                                </button>
                            </div>
                        </div>
                        <pre className="bg-black/20 p-4 rounded-lg text-sm overflow-x-auto">
                            {generateScript(embed)}
                        </pre>

                        {showImportModal && (
                            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                                <div className="bg-[#0A0A0B] border border-white/5 rounded-xl p-6 w-full max-w-lg">
                                    <h3 className="text-lg font-semibold mb-4">
                                        Import Embed Script
                                    </h3>
                                    <textarea
                                        value={importScript}
                                        onChange={e => setImportScript(e.target.value)}
                                        placeholder="Paste your embed script here..."
                                        className="w-full h-32 bg-black/20 border border-white/5 rounded-lg px-3 py-2 mb-4"
                                    />
                                    <div className="flex justify-end gap-3">
                                        <button
                                            onClick={() => {
                                                setShowImportModal(false)
                                                setImportScript("")
                                            }}
                                            className="px-4 py-2 text-sm text-white/60 hover:text-white/80 transition-colors">
                                            Cancel
                                        </button>
                                        <button
                                            onClick={() => {
                                                if (importScript) {
                                                    parseScript(importScript)
                                                    setShowImportModal(false)
                                                    setImportScript("")
                                                }
                                            }}
                                            className="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 rounded-lg transition-colors">
                                            Import
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="w-full bg-[#0A0A0B] border border-white/5 rounded-xl overflow-hidden">
                        <div className="border-b border-white/5 p-6">
                            <h2 className="text-2xl font-bold text-white">Embed Settings</h2>
                        </div>
                        <div className="p-6 space-y-8">
                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">Basic Settings</h3>
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm text-white/60 mb-2">
                                            Color
                                        </label>
                                        <div className="flex gap-2 items-center">
                                            <input
                                                type="color"
                                                value={embed.color}
                                                onChange={e =>
                                                    setEmbed({ ...embed, color: e.target.value })
                                                }
                                                className="w-10 h-10 rounded-lg cursor-pointer border border-white/5 bg-[#0B0C0C] p-1"
                                            />
                                            <input
                                                type="text"
                                                value={embed.color}
                                                onChange={e =>
                                                    setEmbed({ ...embed, color: e.target.value })
                                                }
                                                className="flex-1 bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                                placeholder="#000000"
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm text-white/60 mb-2">
                                            URL
                                        </label>
                                        <input
                                            type="text"
                                            value={embed.url || ""}
                                            onChange={e =>
                                                setEmbed({ ...embed, url: e.target.value })
                                            }
                                            className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                            placeholder="https://example.com"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm text-white/60 mb-2">
                                            Title
                                        </label>
                                        <input
                                            type="text"
                                            value={embed.title || ""}
                                            onChange={e => updateEmbed({ title: e.target.value })}
                                            className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                            maxLength={DISCORD_LIMITS.TITLE}
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm text-white/60 mb-2">
                                            Description
                                        </label>
                                        <textarea
                                            value={embed.description || ""}
                                            onChange={e =>
                                                updateEmbed({ description: e.target.value })
                                            }
                                            className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 min-h-[100px]"
                                            maxLength={DISCORD_LIMITS.DESCRIPTION}
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">Author</h3>
                                <div className="space-y-2">
                                    <input
                                        type="text"
                                        placeholder="Author Name"
                                        value={embed.author?.name || ""}
                                        onChange={e =>
                                            setEmbed({
                                                ...embed,
                                                author: { ...embed.author, name: e.target.value }
                                            })
                                        }
                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                    />
                                    <input
                                        type="text"
                                        placeholder="Author Icon URL"
                                        value={embed.author?.icon_url || ""}
                                        onChange={e =>
                                            setEmbed({
                                                ...embed,
                                                author: {
                                                    ...embed.author,
                                                    icon_url: e.target.value
                                                }
                                            })
                                        }
                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                    />
                                    <input
                                        type="text"
                                        placeholder="Author URL"
                                        value={embed.author?.url || ""}
                                        onChange={e =>
                                            setEmbed({
                                                ...embed,
                                                author: { ...embed.author, url: e.target.value }
                                            })
                                        }
                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-lg font-semibold text-white">Fields</h3>
                                    <button
                                        onClick={() =>
                                            setEmbed({
                                                ...embed,
                                                fields: [
                                                    ...(embed.fields || []),
                                                    { name: "", value: "", inline: false }
                                                ]
                                            })
                                        }
                                        className="text-sm px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg transition-colors">
                                        Add Field
                                    </button>
                                </div>
                                {embed.fields?.map((field, index) => (
                                    <div
                                        key={index}
                                        className="space-y-2 p-4 bg-black/20 rounded-xl">
                                        <div className="flex justify-between">
                                            <span className="text-sm">Field {index + 1}</span>
                                            <button
                                                onClick={() => {
                                                    const newFields = [...(embed.fields || [])]
                                                    newFields.splice(index, 1)
                                                    setEmbed({ ...embed, fields: newFields })
                                                }}
                                                className="text-red-500 hover:text-red-400">
                                                Remove
                                            </button>
                                        </div>
                                        <input
                                            type="text"
                                            placeholder="Field Name"
                                            value={field.name}
                                            onChange={e => {
                                                const newFields = [...(embed.fields || [])]
                                                newFields[index].name = e.target.value
                                                setEmbed({ ...embed, fields: newFields })
                                            }}
                                            className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                        />
                                        <textarea
                                            placeholder="Field Value"
                                            value={field.value}
                                            onChange={e => {
                                                const newFields = [...(embed.fields || [])]
                                                newFields[index].value = e.target.value
                                                setEmbed({ ...embed, fields: newFields })
                                            }}
                                            className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                        />
                                        <div className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                checked={field.inline}
                                                onChange={e => {
                                                    const newFields = [...(embed.fields || [])]
                                                    newFields[index].inline = e.target.checked
                                                    setEmbed({ ...embed, fields: newFields })
                                                }}
                                                className="rounded border-white/5"
                                            />
                                            <label className="text-sm text-white/60">Inline</label>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">Images</h3>
                                <div>
                                    <label className="block text-sm text-white/60 mb-2">
                                        Thumbnail URL
                                    </label>
                                    <input
                                        type="text"
                                        value={embed.thumbnail || ""}
                                        onChange={e =>
                                            setEmbed({ ...embed, thumbnail: e.target.value })
                                        }
                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-white/60 mb-2">
                                        Image URL
                                    </label>
                                    <input
                                        type="text"
                                        value={embed.image || ""}
                                        onChange={e =>
                                            setEmbed({ ...embed, image: e.target.value })
                                        }
                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">Footer</h3>
                                <div className="space-y-2">
                                    <input
                                        type="text"
                                        placeholder="Footer Text"
                                        value={embed.footer?.text || ""}
                                        onChange={e =>
                                            setEmbed({
                                                ...embed,
                                                footer: { ...embed.footer, text: e.target.value }
                                            })
                                        }
                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                    />
                                    <input
                                        type="text"
                                        placeholder="Footer Icon URL"
                                        value={embed.footer?.icon_url || ""}
                                        onChange={e =>
                                            setEmbed({
                                                ...embed,
                                                footer: {
                                                    ...embed.footer,
                                                    icon_url: e.target.value
                                                }
                                            })
                                        }
                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">
                                    Additional Options
                                </h3>
                                <div className="flex items-center gap-3">
                                    <input
                                        type="checkbox"
                                        checked={embed.timestamp}
                                        onChange={e =>
                                            setEmbed({ ...embed, timestamp: e.target.checked })
                                        }
                                        className="rounded border-white/5"
                                    />
                                    <label className="text-sm text-white/60">
                                        Include Timestamp
                                    </label>
                                </div>
                                <div>
                                    <label className="block text-sm text-white/60 mb-2">
                                        Delete After (seconds)
                                    </label>
                                    <input
                                        type="number"
                                        value={embed.delete_after || ""}
                                        onChange={e =>
                                            setEmbed({
                                                ...embed,
                                                delete_after: Number(e.target.value)
                                            })
                                        }
                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                        min="0"
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-lg font-semibold text-white">Buttons</h3>
                                    <button
                                        onClick={() =>
                                            setEmbed({
                                                ...embed,
                                                buttons: [
                                                    ...(embed.buttons || []),
                                                    {
                                                        label: "",
                                                        url: "",
                                                        emoji: "",
                                                        style: "gray",
                                                        disabled: false
                                                    }
                                                ]
                                            })
                                        }
                                        className="text-sm px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg transition-colors">
                                        Add Button
                                    </button>
                                </div>
                                <div className="space-y-3">
                                    {embed.buttons?.map((button, index) => (
                                        <div
                                            key={index}
                                            className="bg-black/20 rounded-lg p-4 space-y-3">
                                            <div className="flex justify-between items-center">
                                                <span className="text-sm text-white/60">
                                                    Button {index + 1}
                                                </span>
                                                <button
                                                    onClick={() => {
                                                        const newButtons = [
                                                            ...(embed.buttons || [])
                                                        ]
                                                        newButtons.splice(index, 1)
                                                        setEmbed({ ...embed, buttons: newButtons })
                                                    }}
                                                    className="text-red-500 hover:text-red-400 text-sm">
                                                    Remove
                                                </button>
                                            </div>
                                            <input
                                                type="text"
                                                placeholder="Label"
                                                value={button.label || ""}
                                                onChange={e => {
                                                    const newButtons = [...(embed.buttons || [])]
                                                    newButtons[index].label = e.target.value
                                                    setEmbed({ ...embed, buttons: newButtons })
                                                }}
                                                className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm"
                                            />
                                            <input
                                                type="text"
                                                placeholder="URL"
                                                value={button.url || ""}
                                                onChange={e => {
                                                    const newButtons = [...(embed.buttons || [])]
                                                    newButtons[index].url = e.target.value
                                                    setEmbed({ ...embed, buttons: newButtons })
                                                }}
                                                className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm"
                                            />
                                            <input
                                                type="text"
                                                placeholder="Emoji (optional)"
                                                value={button.emoji || ""}
                                                onChange={e => {
                                                    const newButtons = [...(embed.buttons || [])]
                                                    newButtons[index].emoji = e.target.value
                                                    setEmbed({ ...embed, buttons: newButtons })
                                                }}
                                                className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm"
                                            />
                                            <div className="flex gap-4">
                                                <div className="flex-1">
                                                    <label className="block text-sm text-white/60 mb-2">
                                                        Style
                                                    </label>
                                                    <select
                                                        value={button.style}
                                                        onChange={e => {
                                                            const newButtons = [
                                                                ...(embed.buttons || [])
                                                            ]
                                                            newButtons[index].style = e.target
                                                                .value as
                                                                | "red"
                                                                | "green"
                                                                | "gray"
                                                                | "blue"
                                                            setEmbed({
                                                                ...embed,
                                                                buttons: newButtons
                                                            })
                                                        }}
                                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm">
                                                        <option value="gray">Gray</option>
                                                        <option value="blue">Blue</option>
                                                        <option value="green">Green</option>
                                                        <option value="red">Red</option>
                                                    </select>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <input
                                                        type="checkbox"
                                                        checked={button.disabled}
                                                        onChange={e => {
                                                            const newButtons = [
                                                                ...(embed.buttons || [])
                                                            ]
                                                            newButtons[index].disabled =
                                                                e.target.checked
                                                            setEmbed({
                                                                ...embed,
                                                                buttons: newButtons
                                                            })
                                                        }}
                                                        className="rounded border-white/5"
                                                    />
                                                    <label className="text-sm text-white/60">
                                                        Disabled
                                                    </label>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">
                                    Message Content
                                </h3>
                                <textarea
                                    value={embed.content || ""}
                                    onChange={e => setEmbed({ ...embed, content: e.target.value })}
                                    placeholder="Message content (outside embed)"
                                    className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 min-h-[100px]"
                                />
                            </div>

                            <div className="flex justify-end">
                                <button
                                    onClick={() => {}}
                                    className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors">
                                    <Save className="w-4 h-4" />
                                    <span>Generate Script</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
