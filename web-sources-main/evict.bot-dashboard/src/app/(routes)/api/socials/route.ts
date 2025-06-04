import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
    const userId = request.headers.get("X-USER-ID")
    if (!userId) {
        return NextResponse.json({ error: "Missing user ID" }, { status: 400 })
    }

    try {
        const response = await fetch(`https://api.evict.bot/socials?t=${Date.now()}`, {
            method: "GET",
            headers: {
                "X-USER-ID": userId,
                Authorization: ""
            },
            credentials: "omit",
            mode: "cors"
        })

        if (!response.ok) {
            throw new Error(`Failed to fetch profile (${response.status})`)
        }

        const data = await response.json()
        return NextResponse.json(data)
    } catch (error) {
        console.error("Failed to fetch profile:", error)
        return NextResponse.json(
            { error: "Failed to fetch profile" },
            { status: 500 }
        )
    }
}