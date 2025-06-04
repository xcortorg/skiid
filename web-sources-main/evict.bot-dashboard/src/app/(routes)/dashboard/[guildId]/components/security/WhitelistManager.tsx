import React, { useState } from 'react';

interface WhitelistManagerProps {
    isOwner: boolean;
    whitelist: string[];
    trustedAdmins: string[];
    onWhitelistChange?: (whitelist: string[]) => void;
    onTrustedAdminsChange?: (admins: string[]) => void;
}

export default function WhitelistManager({ 
    isOwner, 
    whitelist, 
    trustedAdmins,
    onWhitelistChange,
    onTrustedAdminsChange 
}: WhitelistManagerProps) {
    const [newId, setNewId] = useState('');

    const handleAddWhitelist = () => {
        if (newId && onWhitelistChange) {
            onWhitelistChange([...whitelist, newId]);
            setNewId('');
        }
    };

    const handleAddTrustedAdmin = () => {
        if (newId && onTrustedAdminsChange) {
            onTrustedAdminsChange([...trustedAdmins, newId]);
            setNewId('');
        }
    };

    return (
        <div className="relative">
            <div className={`bg-white/[0.02] border border-white/5 rounded-xl p-6 ${!isOwner && 'blur-sm pointer-events-none'}`}>
                <h3 className="text-base font-medium text-white mb-4">Whitelist Management</h3>
                <div className="space-y-4">
                    <div>
                        <h4 className="text-sm text-white/60 mb-2">Whitelisted Users</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {whitelist.map(id => (
                                <div key={id} className="flex items-center justify-between bg-white/5 px-3 py-2 rounded-lg">
                                    <span className="text-sm text-white/80">{id}</span>
                                    <button 
                                        onClick={() => onWhitelistChange?.(whitelist.filter(wId => wId !== id))}
                                        className="text-red-500 hover:text-red-400"
                                    >
                                        Remove
                                    </button>
                                </div>
                            ))}
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={newId}
                                    onChange={(e) => setNewId(e.target.value)}
                                    placeholder="Enter user ID"
                                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm flex-1"
                                />
                                <button
                                    onClick={handleAddWhitelist}
                                    className="bg-blue-500 hover:bg-blue-600 px-3 py-2 rounded-lg text-sm"
                                >
                                    Add
                                </button>
                            </div>
                        </div>
                    </div>
                    <div>
                        <h4 className="text-sm text-white/60 mb-2">Trusted Administrators</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {trustedAdmins.map(id => (
                                <div key={id} className="flex items-center justify-between bg-white/5 px-3 py-2 rounded-lg">
                                    <span className="text-sm text-white/80">{id}</span>
                                    <button 
                                        onClick={() => onTrustedAdminsChange?.(trustedAdmins.filter(aId => aId !== id))}
                                        className="text-red-500 hover:text-red-400"
                                    >
                                        Remove
                                    </button>
                                </div>
                            ))}
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={newId}
                                    onChange={(e) => setNewId(e.target.value)}
                                    placeholder="Enter user ID"
                                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm flex-1"
                                />
                                <button
                                    onClick={handleAddTrustedAdmin}
                                    className="bg-blue-500 hover:bg-blue-600 px-3 py-2 rounded-lg text-sm"
                                >
                                    Add
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            {!isOwner && (
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="bg-black/80 text-white px-4 py-2 rounded-lg">
                        Only the server owner can modify the whitelist
                    </div>
                </div>
            )}
        </div>
    )
} 