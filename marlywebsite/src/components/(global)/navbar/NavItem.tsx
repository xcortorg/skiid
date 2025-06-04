"use client"
import Link from "next/link"

interface NavItemProps {
    label: string
    destination: string
    isActive: boolean
}

const NavItem: React.FC<NavItemProps> = ({ label, destination, isActive, ...props }) => {
    return (
        <Link
            href={destination}
            className={`font-medium ${isActive ? "text-white py-5 pb-8" : "text-white"}`}
            {...props}>
            {label}
        </Link>
    )
}

export default NavItem
