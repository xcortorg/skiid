import { Switch } from "@headlessui/react"

interface ToggleProps {
    enabled: boolean;
    onChange: (enabled: boolean) => void;
    disabled?: boolean;
}

export default function Toggle({ enabled, onChange, disabled = false }: ToggleProps) {
    return (
        <Switch
            checked={enabled}
            onChange={onChange}
            disabled={disabled}
            className={`${enabled ? 'bg-blue-600' : 'bg-white/[0.08]'}
                relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent 
                transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 
                focus-visible:ring-white focus-visible:ring-opacity-75
                ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
            <span
                className={`${enabled ? 'translate-x-5' : 'translate-x-0'}
                    pointer-events-none inline-block h-5 w-5 transform rounded-full 
                    bg-white shadow-lg ring-0 transition duration-200 ease-in-out`}
            />
        </Switch>
    )
} 