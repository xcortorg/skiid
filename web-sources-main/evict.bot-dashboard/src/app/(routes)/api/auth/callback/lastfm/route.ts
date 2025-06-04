import { auth } from "@/auth"
import crypto from "crypto"

export const GET = async (request: Request) => {
    const url = new URL(request.url)
    const token = url.searchParams.get("token")
    
    if (!token) {
        return new Response("No token received", { status: 400 })
    }

    try {
        const params = {
            api_key: process.env.LASTFM_API_KEY!,
            method: 'auth.getSession',
            token: token
        }
        
        const signature = crypto
            .createHash("md5")
            .update(Object.keys(params)
                .sort()
                .map(key => key + params[key as keyof typeof params])
                .join('') + process.env.LASTFM_SECRET)
            .digest("hex")

        const lastfmUrl = `https://ws.audioscrobbler.com/2.0/?method=auth.getSession&api_key=${process.env.LASTFM_API_KEY}&token=${token}&api_sig=${signature}&format=json`

        const response = await fetch(lastfmUrl)
        const data = await response.json()

        if (!data.session?.key) {
            console.error("Last.fm error response:", data)
            return new Response("Failed to get session key", { status: 400 })
        }

        const discordSession = await auth()
        if (!discordSession?.user?.id) {
            return new Response("No Discord session found", { status: 400 })
        }

        const apiResponse = await fetch("https://api.evict.bot/lastfm/auth", {
            method: "POST",
            headers: {
                "Authorization": process.env.NOTHIDDEN_API_KEY ?? "",
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                user_id: discordSession.user.id,
                access_token: data.session.key,
                username: data.session.name
            })
        })

        if (!apiResponse.ok) {
            console.error("API Error:", await apiResponse.text())
            return new Response("Failed to save credentials", { status: 500 })
        }

        return Response.redirect(new URL("/connected", request.url))
    } catch (error) {
        console.error("Auth error:", error)
        return new Response("Authentication failed", { status: 500 })
    }
}