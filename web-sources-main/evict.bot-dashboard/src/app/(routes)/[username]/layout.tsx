export { generateMetadata } from './metadata'

export default function ProfileLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <div>
            {children}
        </div>
    )
} 