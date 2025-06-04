"use client"

import { Dialog, DialogContent } from "@/components/dialog"
import { LogEntry, MessageEditContent, MessageContent, RoleUpdateContent, ChannelUpdateContent, MemberRoleUpdateContent, BulkDeleteContent, MemberContent, MemberUpdateContent, VoiceStateContent, EmojiUpdateContent, EmojiDeleteContent, ApiBaseContent } from "@/libs/dashboard/guild/logging"
import { format, formatDistanceToNow } from "date-fns"
import { FileText, X } from "lucide-react"
import { useState } from "react"

interface LogDetailsModalProps {
    log: LogEntry;
    logs: LogEntry[];
    onClose: () => void;
}

interface ConfirmLinkModalProps {
    url: string
    isOpen: boolean
    onClose: () => void
    onConfirm: () => void
}

interface Change {
    name: string;
    value: string;
    inline?: boolean;
}

function isMessageEditContent(content: LogEntry['content']): content is MessageEditContent {
    return 'message' in content && 'changes' in content.message && content.message.changes?.content !== undefined;
}

function isMessageContent(content: LogEntry['content']): content is MessageContent {
    return 'event' in content && content.event.type === 'MESSAGE' && 
           'changes' in content && Array.isArray(content.changes) && 
           content.changes.some(c => c.name.includes("Message Content"));
}

function isRoleUpdateContent(content: LogEntry['content']): content is RoleUpdateContent {
    return 'role' in content && 'changes' in content
}

function isMemberRoleUpdateContent(content: LogEntry['content']): content is MemberRoleUpdateContent {
    return 'member' in content && 'changes' in content
}

function isChannelUpdateContent(content: LogEntry['content']): content is ChannelUpdateContent {
    return 'channel' in content && 'changes' in content
}

function formatFileSize(bytes: number): string {
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 Byte'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${Math.round(bytes / Math.pow(1024, i))} ${sizes[i]}`
}

function formatDiscordTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    const unix = Math.floor(date.getTime() / 1000);
    return `<t:${unix}:F> (<t:${unix}:R>)`;
}

function formatDiscordText(text: string, users: Record<string, { name: string | null; bot: boolean | null }> = {}) {
    if (!text) return '';
    
    let formattedText = text
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&amp;/g, '&');

    formattedText = formattedText.replace(/<t:(\d+):(F|R)>/g, (match, timestamp, formatType) => {
        const date = new Date(parseInt(timestamp) * 1000);
        return formatType === 'F' ? format(date, "MMM d, yyyy HH:mm") : formatDistanceToNow(date, { addSuffix: true });
    });

    formattedText = formattedText.replace(/<@!?(\d+)>/g, (match, id) => {
        const user = users[id];
        const displayName = user?.name || `user-${id}`;
        return `<span class="text-blue-400 hover:underline cursor-pointer">@${displayName}</span>`;
    });

    formattedText = formattedText.replace(/<#(\d+)>/g, (match, id) => {
        return `<span class="text-blue-400 hover:underline cursor-pointer">#${id}</span>`;
    });

    formattedText = formattedText.replace(/\[(.*?)\]\((.*?)\)/g, (match, text, url) => {
        const cleanText = text.replace(/\*([^*]+)\*/g, '$1');
        return `<a href="javascript:void(0)" data-url="${url}" class="text-blue-400 hover:underline" onclick="window.handleExternalLink(this)">${cleanText}</a>`;
    });

    formattedText = formattedText.split('\n').map(line => {
        if (line.startsWith('> ')) {
            return `<div class="border-l-4 border-zinc-700 pl-3 text-zinc-400">${line.substring(2)}</div>`;
        }
        return line;
    }).join('\n');

    formattedText = formattedText
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/__(.*?)__/g, '<u>$1</u>')
        .replace(/~~(.*?)~~/g, '<del>$1</del>')
        .replace(/`(.*?)`/g, '<code class="bg-black/20 px-1 py-0.5 rounded">$1</code>');

    return formattedText;
}

function ConfirmLinkModal({ url, isOpen, onClose, onConfirm }: ConfirmLinkModalProps) {
    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="bg-[#111111] border-[#222222] text-white p-6">
                <h2 className="text-lg font-semibold mb-4">External Link</h2>
                <p className="text-zinc-400 mb-6">You are leaving this site to visit:</p>
                <p className="bg-[#0B0C0C] p-3 rounded-md text-sm mb-6 break-all">{url}</p>
                <div className="flex justify-end gap-3">
                    <button 
                        onClick={onClose}
                        className="px-4 py-2 rounded-md hover:bg-white/5"
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={onConfirm}
                        className="px-4 py-2 rounded-md bg-blue-500 hover:bg-blue-600"
                    >
                        Continue
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}

function isBulkDeleteContent(content: LogEntry['content']): content is BulkDeleteContent {
    return 'messages' in content && Array.isArray(content.messages)
}

function isMemberContent(content: LogEntry['content']): content is MemberContent {
    return 'member' in content && 'action' in content
}

function isMemberUpdateContent(content: LogEntry['content']): content is MemberUpdateContent {
    return 'member' in content && 'changes' in content && !('roles_granted' in content.changes)
}

function isVoiceStateContent(content: LogEntry['content']): content is VoiceStateContent {
    return 'voice_state' in content
}

function isEmojiUpdateContent(content: LogEntry['content']): content is EmojiUpdateContent {
    return 'emoji' in content && 'changes' in content
}

function isEmojiDeleteContent(content: LogEntry['content']): content is EmojiDeleteContent {
    return 'emoji' in content && !('changes' in content)
}

function isApiContent(content: LogEntry['content']): content is ApiBaseContent {
    return 'event' in content && 'user' in content;
}

export default function LogDetailsModal({ log, logs, onClose }: LogDetailsModalProps) {
    const [linkModal, setLinkModal] = useState<{ isOpen: boolean; url: string }>({ isOpen: false, url: "" })
    const users: Record<string, { name: string | null; bot: boolean | null }> = {};
    const channels: Record<string, { name: string; type: string }> = {};

    const processLogEntry = (logEntry: LogEntry) => {
        if ('author' in logEntry.content && logEntry.content.author) {
            users[logEntry.content.author.id] = {
                name: logEntry.content.author.name || logEntry.content.author.display_name,
                bot: logEntry.content.author.bot
            }
        }
        if ('user' in logEntry.content && logEntry.content.user) {
            users[logEntry.content.user.id] = {
                name: logEntry.content.user.name,
                bot: logEntry.content.user.bot
            }
        }
        if ('member' in logEntry.content && logEntry.content.member) {
            users[logEntry.content.member.id] = {
                name: logEntry.content.member.display_name || logEntry.content.member.name,
                bot: 'bot' in logEntry.content.member ? logEntry.content.member.bot : false
            }
        }

        if ('channel' in logEntry.content && logEntry.content.channel) {
            channels[logEntry.content.channel.id] = {
                name: logEntry.content.channel.name,
                type: logEntry.content.channel.type
            }
        }
        if ('target' in logEntry.content && logEntry.content.target?.channel_id) {
            channels[logEntry.content.target.channel_id] = {
                name: logEntry.content.target.channel_name || 'unknown',
                type: logEntry.content.target.channel_type || 'unknown'
            }
        }

        if ('details' in logEntry.content && typeof logEntry.content.details === 'string') {
            const userMentions = logEntry.content.details.match(/<@!?(\d+)>/g) || [];
            userMentions.forEach(mention => {
                const id = mention.match(/\d+/)?.[0];
                if (id && !users[id]) {
                    users[id] = { name: null, bot: null };
                }
            });
        }
    }

    if (logs) {
        logs.forEach(processLogEntry);
    }

    users["1203514684326805524"] = {
        name: "evict",
        bot: true
    };

    if (typeof window !== 'undefined') {
        window.handleExternalLink = (element: HTMLAnchorElement) => {
            const url = element.getAttribute('data-url')
            if (url) {
                setLinkModal({ isOpen: true, url })
            }
        }
    }

    if (!log) return null

    return (
        <>
            <Dialog open={!!log} onOpenChange={() => onClose()}>
                <DialogContent className="bg-[#111111] border-[#222222] text-white p-0 gap-0 max-w-4xl max-h-[85vh] overflow-y-auto">
                    <div className="p-6 space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="space-y-1">
                                <h2 className="text-lg font-semibold flex items-center gap-2">
                                    <span className="px-2 py-1 rounded-md text-xs bg-white/10">
                                        {log.event_type}
                                        {('action' in log.content && log.content.action) && (
                                            <span className="ml-1">• {log.content.action.replace(/_/g, ' ')}</span>
                                        )}
                                        {('event' in log.content && log.content.event?.type) && (
                                            <span className="ml-1">• {log.content.event.type.replace(/_/g, ' ')}</span>
                                        )}
                                    </span>
                                    <span className="text-zinc-400 text-sm">
                                        {format(new Date(log.created_at), "MMM d, yyyy HH:mm")}
                                    </span>
                                </h2>
                            </div>
                            <button 
                                onClick={() => onClose()}
                                className="rounded-md p-2 hover:bg-white/5"
                            >
                                <X className="h-4 w-4 text-zinc-400" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            {'target' in log.content && log.content.target && (
                                Object.values(log.content.target).some(value => value !== null) && (
                                    <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                        <h3 className="text-sm font-medium mb-2">Target Information</h3>
                                        <div className="space-y-1 text-sm text-zinc-400">
                                            {log.content.target.channel_name && (
                                                <div>Channel: <span className="text-white">#{log.content.target.channel_name}</span></div>
                                            )}
                                            {log.content.target.channel_type && log.content.target.channel_type !== '<class \'discord.object.Object\'>' && (
                                                <div>Type: <span className="text-white">{log.content.target.channel_type}</span></div>
                                            )}
                                        </div>
                                    </div>
                                )
                            )}

                            {'user' in log.content && log.content.user && (
                                <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                    <h3 className="text-sm font-medium mb-2">User Information</h3>
                                    <div className="flex items-center gap-2">
                                        <span className="text-blue-400 hover:underline cursor-pointer">@{log.content.user.name}</span>
                                        {log.content.user.bot && (
                                            <span className="px-1 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-500">BOT</span>
                                        )}
                                    </div>
                                </div>
                            )}

                            {'changes' in log.content && log.content.changes && (
                                Array.isArray(log.content.changes) ? 
                                    log.content.changes.length > 0 && (
                                        <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                            <h3 className="text-sm font-medium mb-2">Changes</h3>
                                            <div className="flex flex-col gap-4">
                                                {log.content.changes.map((change: Change, index) => (
                                                    <div key={index} className="text-sm flex flex-col gap-1">
                                                        <div className="font-medium text-zinc-400 break-all">{change.name.replace(/\*\*/g, '')}</div>
                                                        <div 
                                                            className="text-white break-all"
                                                            dangerouslySetInnerHTML={{ 
                                                                __html: formatDiscordText(change.value, users)
                                                            }}
                                                        />
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ) : Object.values(log.content.changes).some(value => value !== undefined) && (
                                        <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                            <h3 className="text-sm font-medium mb-2">Changes</h3>
                                        </div>
                                    )
                            )}

                            {'details' in log.content && log.content.details && (
                                <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                    <h3 className="text-sm font-medium mb-2">Additional Details</h3>
                                    <div 
                                        className="text-sm text-zinc-400 break-words [&_a]:text-blue-400 [&_a]:hover:underline"
                                        dangerouslySetInnerHTML={{ 
                                            __html: formatDiscordText(typeof log.content.details === 'string' ? log.content.details : '', users)
                                        }}
                                    />
                                </div>
                            )}

                            {isMemberContent(log.content) && (
                                <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                    <h3 className="text-sm font-medium mb-2">Member Information</h3>
                                    <div className="space-y-2">
                                        <div className="flex items-center gap-2">
                                            <span className="text-blue-400 hover:underline cursor-pointer">@{log.content.member.name}</span>
                                            {log.content.member.bot && (
                                                <span className="px-1 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-500">BOT</span>
                                            )}
                                        </div>
                                        <div className="text-sm text-zinc-400">
                                            <div>Action: {log.content.action}</div>
                                            <div>Joined: {log.content.member.joined_at ? format(new Date(log.content.member.joined_at), "MMM d, yyyy HH:mm") : 'N/A'}</div>
                                            {'details' in log.content && log.content.details?.new_account && (
                                                <div className="text-yellow-400">New Account</div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {isMemberUpdateContent(log.content) && log.content.changes && Object.keys(log.content.changes).length > 0 && (
                                <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                    <h3 className="text-sm font-medium mb-2">Member Update</h3>
                                    <div className="space-y-2">
                                        {log.content.changes.nickname && (
                                            <div className="text-sm">
                                                <div className="text-zinc-400">Nickname:</div>
                                                <div>Before: {log.content.changes.nickname.before || 'None'}</div>
                                                <div>After: {log.content.changes.nickname.after || 'None'}</div>
                                            </div>
                                        )}
                                        {log.content.changes.roles && (
                                            <div className="text-sm">
                                                <div className="text-zinc-400">Roles:</div>
                                                <div>Removed: {log.content.changes.roles.before.join(', ') || 'None'}</div>
                                                <div>Added: {log.content.changes.roles.after.join(', ') || 'None'}</div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {isVoiceStateContent(log.content) && (
                                <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                    <h3 className="text-sm font-medium mb-2">Voice State Update</h3>
                                    <div className="space-y-2 text-sm">
                                        <div>Action: {log.content.action}</div>
                                        {log.content.changes.channel && (
                                            <div>
                                                <div>From: {log.content.changes.channel.before || 'None'}</div>
                                                <div>To: {log.content.changes.channel.after || 'None'}</div>
                                            </div>
                                        )}
                                        <div className="grid grid-cols-2 gap-2">
                                            <div>Self Mute: {log.content.voice_state.self_mute ? 'Yes' : 'No'}</div>
                                            <div>Self Deaf: {log.content.voice_state.self_deaf ? 'Yes' : 'No'}</div>
                                            <div>Streaming: {log.content.voice_state.self_stream ? 'Yes' : 'No'}</div>
                                            <div>Video: {log.content.voice_state.self_video ? 'Yes' : 'No'}</div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {(isEmojiUpdateContent(log.content) || isEmojiDeleteContent(log.content)) && (
                                <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                    <h3 className="text-sm font-medium mb-2">Emoji Information</h3>
                                    <div className="space-y-2 text-sm">
                                        <div>Name: {log.content.emoji.name}</div>
                                        {isEmojiUpdateContent(log.content) && log.content.changes.name && (
                                            <div>
                                                <div>Old Name: {log.content.changes.name.before}</div>
                                                <div>New Name: {log.content.changes.name.after}</div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {log.content.event?.files && log.content.event.files.length > 0 && (
                                <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                    <h3 className="text-sm font-medium mb-2">Files</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {log.content.event.files.map((file, index) => (
                                            <a
                                                key={index}
                                                href={file}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-1 px-2 py-1 rounded-md bg-white/5 hover:bg-white/10 text-xs text-zinc-400"
                                            >
                                                <FileText className="w-3 h-3" />
                                                <span>{file.split('/').pop()}</span>
                                            </a>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {isBulkDeleteContent(log.content) && (
                                <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                    <h3 className="text-sm font-medium mb-2">Deleted Messages</h3>
                                    <div className="space-y-3">
                                        {log.content.messages.map((message) => (
                                            <div key={message.id} className="text-sm border-b border-[#222222] last:border-0 pb-3 last:pb-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-blue-400">@{message.author.name}</span>
                                                    <span className="text-zinc-500 text-xs">
                                                        {format(new Date(message.created_at), "HH:mm:ss")}
                                                    </span>
                                                </div>
                                                <div className="text-zinc-300">{message.content}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {isMessageEditContent(log.content) && (
                                <div className="bg-[#0B0C0C] rounded-xl border border-[#222222] p-4">
                                    <h3 className="text-sm font-medium mb-2">Message Edit</h3>
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-blue-400">@{log.content.author.name}</span>
                                            {log.content.author.bot && (
                                                <span className="px-1 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-500">BOT</span>
                                            )}
                                        </div>
                                        <div className="space-y-2">
                                            <div className="text-sm">
                                                <div className="text-zinc-400 mb-1">Before:</div>
                                                <div className="text-white">{log.content.message.changes.content?.before ?? 'No content'}</div>
                                            </div>
                                            <div className="text-sm">
                                                <div className="text-zinc-400 mb-1">After:</div>
                                                <div className="text-white">{log.content.message.changes.content?.after ?? 'No content'}</div>
                                            </div>
                                        </div>
                                        <a 
                                            href={log.content.message.jump_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-blue-400 hover:underline"
                                        >
                                            Jump to Message
                                        </a>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            <ConfirmLinkModal 
                url={linkModal.url}
                isOpen={linkModal.isOpen}
                onClose={() => setLinkModal({ isOpen: false, url: "" })}
                onConfirm={() => {
                    window.open(linkModal.url, '_blank', 'noopener,noreferrer')
                    setLinkModal({ isOpen: false, url: "" })
                }}
            />
        </>
    )
}

declare global {
    interface Window {
        handleExternalLink: (element: HTMLAnchorElement) => void
    }
} 