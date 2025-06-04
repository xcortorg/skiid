import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
    const host = request.headers.get('host')
    
    if (host === 'cname.evict.bot') {
        return NextResponse.redirect('https://evict.bot')
    }

    try {
        const response = await fetch(`https://api.evict.bot/domains/verify?domain=${host}`, {
            headers: {
                "Authorization": ""
            }
        })
        
        const data = await response.json()
        
        if (!response.ok) {
            return NextResponse.redirect('https://evict.bot')
        }

        if (data.success && data.owner) {
            return NextResponse.rewrite(new URL(`/@${data.owner}`, request.url))
        }

        return NextResponse.redirect('https://evict.bot')
    } catch {
        return NextResponse.redirect('https://evict.bot')
    }
}