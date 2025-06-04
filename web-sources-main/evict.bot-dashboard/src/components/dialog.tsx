"use client"

import { useEffect } from "react"
import { X } from "lucide-react"

interface DialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    children: React.ReactNode
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
    useEffect(() => {
        if (open) {
            document.body.style.overflow = 'hidden'
        } else {
            document.body.style.overflow = 'unset'
        }

        return () => {
            document.body.style.overflow = 'unset'
        }
    }, [open])

    if (!open) return null

    return (
        <div className="fixed inset-0 z-50 bg-black/80">
            <div className="fixed inset-0 z-50 flex items-center justify-center">
                {children}
            </div>
        </div>
    )
}

interface DialogContentProps {
    children: React.ReactNode
    className?: string
}

export function DialogContent({ children, className = "" }: DialogContentProps) {
    return (
        <div className={`relative bg-[#111111] rounded-xl shadow-lg w-full max-w-lg mx-4 ${className}`}>
            {children}
        </div>
    )
} 