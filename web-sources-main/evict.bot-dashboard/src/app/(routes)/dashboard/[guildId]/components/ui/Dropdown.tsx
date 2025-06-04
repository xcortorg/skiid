import { Fragment, useState } from 'react'
import { Listbox, Transition } from '@headlessui/react'
import { ChevronDown, Search } from 'lucide-react'

interface DropdownProps {
    value: string | null
    onChange: (value: string) => void
    placeholder: string
    options: {
        id: string
        name: string
        color?: number
        category?: boolean
    }[]
    className?: string
    searchable?: boolean
}

export default function Dropdown({ value, onChange, placeholder, options, className = '', searchable = false }: DropdownProps) {
    const [search, setSearch] = useState('')
    const selected = options.find(option => option.id === value)
    
    const filteredOptions = searchable 
        ? options.filter(option => option.name.toLowerCase().includes(search.toLowerCase()))
        : options

    return (
        <Listbox value={value} onChange={onChange}>
            <div className="relative">
                <Listbox.Button className={`relative w-full cursor-pointer rounded-lg bg-[#0B0C0C] py-2 pl-3 pr-10 text-left border border-white/10 focus:outline-none focus-visible:border-white/20 text-sm ${className}`}>
                    <span className="block truncate text-white/60">
                        {selected ? (
                            <span style={selected.color ? { color: `#${selected.color.toString(16).padStart(6, '0')}` } : {}}>
                                {selected.name}
                            </span>
                        ) : (
                            placeholder
                        )}
                    </span>
                    <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                        <ChevronDown className="h-4 w-4 text-white/60" aria-hidden="true" />
                    </span>
                </Listbox.Button>
                <Transition
                    as={Fragment}
                    leave="transition ease-in duration-100"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                >
                    <Listbox.Options className="absolute mt-1 max-h-60 w-full overflow-auto rounded-lg bg-[#0B0C0C] border border-white/10 py-1 text-sm shadow-lg focus:outline-none z-50">
                        {searchable && (
                            <div className="px-3 py-2 border-b border-white/10">
                                <div className="relative">
                                    <input
                                        type="text"
                                        className="w-full bg-black/20 rounded px-3 py-1 pl-8 text-white placeholder-white/40 border border-white/10"
                                        placeholder="Search..."
                                        value={search}
                                        onChange={(e) => setSearch(e.target.value)}
                                    />
                                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                                </div>
                            </div>
                        )}
                        {filteredOptions.map((option) => (
                            <Listbox.Option
                                key={option.id}
                                value={option.id}
                                className={({ active }) =>
                                    `relative cursor-pointer select-none py-2 pl-3 pr-9 ${
                                        active ? 'bg-white/5' : ''
                                    } ${option.category ? 'text-white/40 font-medium' : 'text-white/80'}`
                                }
                                disabled={option.category}
                            >
                                <span 
                                    className={`block truncate ${value === option.id ? 'font-medium' : 'font-normal'}`}
                                    style={option.color ? { color: `#${option.color.toString(16).padStart(6, '0')}` } : {}}
                                >
                                    {option.name}
                                </span>
                            </Listbox.Option>
                        ))}
                    </Listbox.Options>
                </Transition>
            </div>
        </Listbox>
    )
} 