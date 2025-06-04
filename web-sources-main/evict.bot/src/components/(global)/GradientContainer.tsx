"use client"

import { MeshGradient } from "./GradientMesh"

export function GradientContainer() {
    return (
        <div className="fixed inset-0 transition-[filter] duration-500">
            <MeshGradient />
        </div>
    )
}
