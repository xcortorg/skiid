import "@/styles/globals.css"
import Image from "next/image"
import Link from "next/link"
import marly from "../../../public/marly.gif"

export const Footer = () => {
    return (
        <div className="mt-[30vh] border-t border-marly-card-border bg-[#0B0C0C] footer pb-10">
            <div className="flex w-full border-solid border-t border-marly-600 border-opacity-10">
                <div className="flex flex-row w-full mt-10 justify-between ">
                    <div className="flex flex-col">
                        <Image
                            src={marly}
                            alt="marly"
                            height={150}
                            width={150}
                            className="rounded-2xl"
                        />
                    </div>
                    <div className="flex flex-col gap-6 sm:flex-row">
                        <div className="flex flex-col">
                            <span className="font-extrabold text-2xl text-white">Bot</span>
                            <Link
                                href="/invite"
                                className="font-semibold text-marly-main text-sm mt-2">
                                Invite
                            </Link>
                            <Link
                                href="https://docs.marly.bot/"
                                className="font-semibold text-marly-main text-sm mt-2">
                                Documentation
                            </Link>
                            <Link
                                href="https://discord.gg/marly"
                                className="font-semibold text-marly-main text-sm mt-2">
                                Support Server
                            </Link>
                        </div>
                        <div className="flex flex-col">
                            <span className="font-extrabold text-2xl text-white">Legal</span>
                            <Link
                                href="/terms"
                                className="font-semibold text-marly-main text-sm mt-2">
                                Terms
                            </Link>
                            <Link
                                href="/privacy"
                                className="font-semibold text-marly-main text-sm mt-2">
                                Privacy
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
