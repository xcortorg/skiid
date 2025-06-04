interface SaveButtonProps {
    hasChanges: boolean;
    isSaving: boolean;
    onSave: () => void;
}

export default function SaveButton({ hasChanges, isSaving, onSave }: SaveButtonProps) {
    if (!hasChanges) return null;

    return (
        <div className="fixed bottom-6 right-6 flex items-center gap-4">
            <div className="bg-white/10 text-white/60 px-4 py-2 rounded-lg text-sm">
                You have unsaved changes
            </div>
            <button
                onClick={onSave}
                disabled={isSaving}
                className="bg-white text-black px-6 py-2 rounded-lg font-medium hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
                {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
        </div>
    )
} 