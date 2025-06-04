import { X } from "lucide-react"
import { format } from "date-fns"
import { ModCase, UserData } from "@/libs/dashboard/guild/modlogs"

interface CaseDetailsModalProps {
    case_: ModCase
    user: UserData | undefined
    moderator: UserData | undefined
    onClose: () => void
}

function getActionColor(action: string) {
    switch (action.toLowerCase()) {
        case 'ban':
            return 'bg-red-500/10 text-red-500'
        case 'kick':
            return 'bg-orange-500/10 text-orange-500'
        case 'mute':
        case 'timeout':
            return 'bg-yellow-500/10 text-yellow-500'
        case 'warn':
            return 'bg-blue-500/10 text-blue-500'
        default:
            return 'bg-white/10 text-white'
    }
}

export default function CaseDetailsModal({ case_, user, moderator, onClose }: CaseDetailsModalProps) {
    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-[#111111] border border-[#222222] rounded-xl w-full max-w-lg mx-4">
                <div className="flex items-center justify-between p-4 border-b border-[#222222]">
                    <h3 className="text-lg font-medium text-white">Case #{case_.case_id}</h3>
                    <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                        <X className="w-5 h-5 text-white/60" />
                    </button>
                </div>
                
                <div className="p-4 space-y-4">
                    <div className="space-y-2">
                        <div className="text-sm text-white/40">User</div>
                        <div className="flex items-center gap-3">
                            <img 
                                src={user?.user_avatar || "https://cdn.discordapp.com/embed/avatars/0.png"}
                                alt={user?.user_name || "Unknown"}
                                className="w-10 h-10 rounded-full"
                            />
                            <div>
                                <div className="text-white">{user?.user_name || "Unknown"}</div>
                                <div className="text-sm text-white/40">{user?.user_id}</div>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <div className="text-sm text-white/40">Action</div>
                        <span className={`
                            px-2 py-1 rounded-full text-sm font-medium
                            ${getActionColor(case_.action)}
                        `}>
                            {case_.action}
                        </span>
                    </div>

                    {case_.duration && (
                        <div className="space-y-2">
                            <div className="text-sm text-white/40">Duration</div>
                            <div className="text-white">{case_.duration}</div>
                        </div>
                    )}

                    <div className="space-y-2">
                        <div className="text-sm text-white/40">Reason</div>
                        <div className="text-white">{case_.reason || "No reason provided"}</div>
                    </div>

                    <div className="space-y-2">
                        <div className="text-sm text-white/40">Moderator</div>
                        <div className="flex items-center gap-3">
                            <img 
                                src={moderator?.user_avatar || "https://cdn.discordapp.com/embed/avatars/0.png"}
                                alt={moderator?.user_name || "Unknown"}
                                className="w-10 h-10 rounded-full"
                            />
                            <div>
                                <div className="text-white">{moderator?.user_name || "Unknown"}</div>
                                <div className="text-sm text-white/40">{moderator?.user_id}</div>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <div className="text-sm text-white/40">Date</div>
                        <div className="text-white">
                            {format(new Date(case_.timestamp), "MMMM d, yyyy 'at' h:mm a")}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
} 