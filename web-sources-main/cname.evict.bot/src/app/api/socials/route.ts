import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
    const userId = request.headers.get("X-USER-ID")
    console.log("Received userId:", userId)

    if (!userId) {
        return NextResponse.json({ error: "Missing user ID" }, { status: 400 })
    }

    const url = `https://api.evict.bot/socials?t=${Date.now()}`
    console.log("Fetching from:", url)

    try {
        const response = await fetch(url, {
            method: "GET",
            headers: {
                "X-USER-ID": userId,
                "Authorization": ""
            }
        })

        console.log("Response status:", response.status)

        if (!response.ok) {
            console.log(response)
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