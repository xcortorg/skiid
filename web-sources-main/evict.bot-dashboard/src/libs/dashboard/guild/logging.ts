export interface BaseEvent {
    type: string;
    timestamp: string;
    files?: string[];
    details?: string;
}

export interface Moderator {
    id: string | null;
    name: string | null;
    bot: boolean | null;
}

export interface MessageAttachment {
    filename: string;
    url: string;
    size: number;
    is_spoiler: boolean;
}

export interface MessageSticker {
    id: string;
    name: string;
    url: string;
}

export interface MessageContent {
    event: BaseEvent;
    message: {
        id: string;
        content: string;
        created_at: string;
        attachments: MessageAttachment[];
        stickers: MessageSticker[];
        embeds: any[]; 
    };
    channel: {
        id: string;
        name: string;
        type: string;
    };
    author: {
        id: string;
        name: string;
        display_name: string;
        bot: boolean;
    };
}

export interface MessageEditContent {
    event: BaseEvent;
    message: {
        id: string;
        jump_url: string;
        changes: {
            content?: { before: string; after: string; };
            attachments?: {
                before: MessageAttachment[];
                after: MessageAttachment[];
            };
            embeds?: {
                before: any[];
                after: any[];
            };
        };
    };
    channel: {
        id: string;
        name: string;
        type: string;
    };
    author: {
        id: string;
        name: string;
        display_name: string;
        bot: boolean;
    };
}
export interface BulkDeleteContent {
    event: BaseEvent;
    channel: {
        id: string;
        name: string;
        type: string;
    };
    messages: Array<{
        id: string;
        content: string;
        author: {
            id: string;
            name: string;
            bot: boolean;
        };
        created_at: string;
        attachments: Array<{
            filename: string;
            url: string;
            size: number;
            is_spoiler: boolean;
        }>;
    }>;
    count: number;
    moderator: Moderator | null;
}

export interface RoleContent {
    event: BaseEvent;
    role: {
        id: string;
        name: string;
        color: string;
        position: number;
        permissions: number;
        is_integration?: boolean;
        icon_url: string | null;
    };
    moderator: Moderator | null;
}

export interface RoleUpdateContent extends RoleContent {
    changes: {
        name?: { before: string; after: string; };
        color?: { before: string; after: string; };
        permissions?: Array<{
            permission: string;
            before: boolean;
            after: boolean;
        }>;
    };
}

export interface MemberRoleUpdateContent {
    event: BaseEvent;
    member: {
        id: string;
        name: string;
        display_name: string;
    };
    changes: {
        roles_granted: Array<{ id: string; name: string; }>;
        roles_removed: Array<{ id: string; name: string; }>;
    };
    moderator: Moderator | null;
}

export interface ChannelContent {
    event: BaseEvent;
    channel: {
        id: string;
        name: string;
        type: string;
        created_at: string;
        category_id?: string | null;
    };
    moderator: Moderator | null;
}

export interface ChannelUpdateContent extends ChannelContent {
    changes: {
        name?: { before: string; after: string; };
        topic?: { before: string | null; after: string | null; };
        nsfw?: { before: boolean; after: boolean; };
        bitrate?: { before: number; after: number; };
        user_limit?: { before: number; after: number; };
        slowmode_delay?: { before: number; after: number; };
    };
}

export interface InviteContent {
    event: BaseEvent;
    invite: {
        code: string;
        url: string;
        max_uses: number | null;
        temporary: boolean;
    };
    moderator: Moderator | null;
}

export interface InviteDeleteContent extends InviteContent {
    invite: {
        code: string;
        url: string;
        uses: number;
        max_uses: number | null;
        temporary: boolean;
        inviter?: {
            id: string;
            name: string;
            bot: boolean;
        };
    };
}

export interface EmojiContent {
    event: BaseEvent;
    emoji: {
        id: string;
        name: string;
        url: string;
    };
    moderator: Moderator | null;
}

export interface MemberContent {
    event: BaseEvent;
    member: {
        id: string;
        name: string;
        display_name: string;
        bot: boolean;
        created_at: string;
        joined_at: string | null;
        roles: string[];
        avatar_url: string;
    };
    action: "JOIN" | "LEAVE" | "UPDATE";
    details?: {
        new_account?: boolean;
    };
}

export interface MemberUpdateContent {
    event: BaseEvent;
    member: {
        id: string;
        name: string;
        display_name: string;
        bot: boolean;
        roles: string[];
    };
    changes: {
        nickname?: { before: string | null; after: string | null; };
        avatar?: { before: string | null; after: string | null; };
        roles?: { 
            before: string[];
            after: string[];
        };
    };
    moderator: Moderator | null;
}

export interface VoiceStateContent {
    event: BaseEvent;
    member: {
        id: string;
        name: string;
        display_name: string;
    };
    action: "JOIN" | "LEAVE" | "MOVE" | "MUTE" | "DEAFEN" | "VIDEO" | "STREAM";
    changes: {
        channel?: { before: string | null; after: string | null; };
        self_mute?: { before: boolean; after: boolean; };
        self_deaf?: { before: boolean; after: boolean; };
        self_video?: { before: boolean; after: boolean; };
        self_stream?: { before: boolean; after: boolean; };
    };
    voice_state: {
        channel_id: string | null;
        self_mute: boolean;
        self_deaf: boolean;
        self_stream: boolean;
        self_video: boolean;
        muted: boolean;
        deafened: boolean;
    };
}

export interface EmojiUpdateContent extends EmojiContent {
    changes: {
        name?: { before: string; after: string; };
    };
}

export interface EmojiDeleteContent {
    event: BaseEvent;
    emoji: {
        id: string;
        name: string;
    };
    moderator: Moderator | null;
}

export interface ApiBaseContent {
    event: BaseEvent;
    user?: {
        id: string;
        bot: boolean;
        name: string;
    };
    author?: {
        id: string;
        bot: boolean;
        name: string;
        display_name: string;
    };
    target?: {
        channel_id: string | null;
        channel_name: string | null;
        channel_type: string | null;
    };
    changes?: Array<{
        name: string;
        value: string;
        inline: boolean;
    }>;
    details?: string;
}

export interface LogEntry {
    id: string;
    guild_id: string;
    channel_id: string | null;
    event_type: string;
    content: MessageContent | MessageEditContent | RoleContent | RoleUpdateContent |
             MemberRoleUpdateContent | ChannelContent | ChannelUpdateContent |
             InviteContent | InviteDeleteContent | EmojiContent | BulkDeleteContent |
             MemberContent | MemberUpdateContent | VoiceStateContent | 
             EmojiUpdateContent | EmojiDeleteContent | ApiBaseContent;
    created_at: string;
}

export interface LoggingChannel {
    channel_id: string;
    channel_name: string;
    events: number;
    enabled_events: string[];
}

export interface LoggingResponse {
    guild_id: string;
    enabled: boolean;
    channels: LoggingChannel[];
    available_events: {
        [key: string]: number;
    };
    logs: LogEntry[];
}

export interface ErrorResponse {
    error: string;
}

export async function fetchGuildLogging(guildId: string): Promise<LoggingResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch("https://api.evict.bot/logging", {
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-GUILD-ID': guildId
        }
    })

    if (!response.ok) {
        const error = await response.json() as ErrorResponse
        throw new Error(error.error || 'Failed to fetch logging settings')
    }

    return response.json()
}
