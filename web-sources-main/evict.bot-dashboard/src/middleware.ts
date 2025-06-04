import { auth } from "@/auth"
import { NextResponse } from "next/server"

export default auth((req) => {
    if (req.nextUrl.pathname.startsWith('/dashboard')) {
        return NextResponse.next()
    }
    
    if (req.nextUrl.pathname === "/" || req.nextUrl.pathname === "/login") {
        return NextResponse.next()
    }

    if (!req.auth) {
        return NextResponse.redirect(new URL("/login", req.url))
    }

    return NextResponse.next()
})

export const config = {
    matcher: [
        "/((?!dashboard|api|_next/static|_next/image|favicon.ico).*)"
    ]
}
