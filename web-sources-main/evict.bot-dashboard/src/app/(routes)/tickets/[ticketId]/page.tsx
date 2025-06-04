import { auth } from "@/auth"
import TicketTranscriptPage from "@/components/(global)/Ticket"

export default async function Page({ params }: { params: { ticketId: string } }) {
    const session = await auth()

    return <TicketTranscriptPage session={session} params={params} />
}
