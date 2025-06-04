import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/auth"
const API_TOKEN = process.env.API_TOKEN || ""

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams
    const id = searchParams.get("id")

    if (!id) {
        return NextResponse.json({ error: "Missing ticket ID" }, { status: 400 })
    }

    const session = await auth() 

    if (!session?.user?.id) {
        return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    try {
        const response = await fetch(`https://api.evict.bot/tickets?id=${id}`, {
            headers: {
                Authorization: `${API_TOKEN}`,
                "User-ID": session.user.id 
            }
        })

        if (response.status === 403) {
            return NextResponse.json({ error: "User is not allowed to view this ticket" }, { status: 403 })
        }

        if (!response.ok) {
            throw new Error(`API responded with status: ${response.status}`)
        }

        const data = await response.json()
        return NextResponse.json(data)
    } catch (error) {
        console.error("Error fetching ticket:", error)
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 })
    }
}
