import Toggle from "./Toggle";

interface ProtectionSettingsProps {
    title: string;
    description: string;
    enabled: boolean;
    onToggle: (enabled: boolean) => void;
    disabled?: boolean;
}

export default function ProtectionSettings({ 
    title, 
    description, 
    enabled, 
    onToggle,
    disabled = false 
}: ProtectionSettingsProps) {
    return (
        <div className="flex items-center justify-between">
            <div className="space-y-1">
                <h3 className="text-sm font-medium text-white">{title}</h3>
                <p className="text-sm text-white/60">{description}</p>
            </div>
            <Toggle 
                enabled={enabled} 
                onChange={onToggle}
                disabled={disabled}
            />
        </div>
    )
} 