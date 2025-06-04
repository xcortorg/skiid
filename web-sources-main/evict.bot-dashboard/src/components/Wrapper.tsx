"use client"

interface WrapperProps {
    children?: React.ReactNode
}

const Wrapper: React.FC<WrapperProps> = ({ children }) => {
    return <div className="min-h-screen w-full bg-background">{children}</div>
}

export default Wrapper
