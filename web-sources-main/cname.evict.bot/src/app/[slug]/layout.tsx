export { generateMetadata } from './metadata'

export default function ProfileLayout({
    children,
}: {
    children: React.ReactNode,
    params: Promise<{ slug: string }>
}) {
    return (
        <div>
            {children}
        </div>
    )
} 