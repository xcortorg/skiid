import "@/components/ticket/styles/discord-buttons.css"
import { ReactElement } from "react"
import { PropsWithSlot } from "../util"

export default function DiscordButtons({ children }: PropsWithSlot): ReactElement {
    return <div className="discord-buttons">{children}</div>
}
