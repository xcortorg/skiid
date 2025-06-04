import { ReactNode } from "react"

export interface BaseCategory {
    name: string
    icon: ReactNode
}

export interface Category {
    name: string
    icon: ReactNode
    commands: Command[]
}

export interface Command {
    name: string
    description: string
    aliases: string[]
    parameters: Parameter[]
    category: string
    donator: boolean
    permissions: string[]
}

export interface Parameter {
    name: string
    type: string
    default: string | null
    flags: {
        required: Flag[]
        optional: Flag[]
    } | null
    optional: boolean
}

export interface Flag {
    name: string
    description: string
}

export interface CommandsResponse {
    categories: string[]
    commands: Command[]
}
