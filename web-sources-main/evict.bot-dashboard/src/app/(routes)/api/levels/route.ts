import { NextRequest, NextResponse } from "next/server";
const API_TOKEN = process.env.API_TOKEN || "";

export async function GET(request: NextRequest) {
    const guildId = request.headers.get("X-GUILD-ID");

    if (!guildId) {
        return NextResponse.json({ error: "Missing guild ID" }, { status: 400 });
    }

    try {
        // Additional Note from the Pro Developer Adam
        // The reason why we are using the _=Date.now() is to prevent the API from caching the response
        const response = await fetch(`https://api.evict.bot/levels?_=${Date.now()}`, {
            headers: {
                Authorization: `${API_TOKEN}`,
                "X-GUILD-ID": guildId,
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Expires": "0",
                "Surrogate-Control": "no-store"
            },
        });

        if (!response.ok) {
            throw new Error(`API responded with status: ${response.status}. If you are a user, please contact the @66adam`);
        }

        const textData = await response.text();
        return new NextResponse(textData, {
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-store',
                'Pragma': 'no-cache',
                'Expires': '0',
                'Surrogate-Control': 'no-store'
            }
        });
    } catch (error) {
        return NextResponse.json({ error: "Internal Server Error. Guild most likely does not have any level data or does not exist." }, { status: 500 });
    }
}