import { auth } from "@/auth"
import { NextResponse } from "next/server"

export default auth(req => {
    const hostname = req.headers.get("host") || "localhost:3000"
    const protocol = process.env.NODE_ENV === "development" ? "http" : "https"
    const baseUrl = `${protocol}://${hostname}`

    if (req.nextUrl.pathname.startsWith("/dashboard")) {
        return NextResponse.next()
    }

    if (req.nextUrl.pathname === "/" || req.nextUrl.pathname === "/login") {
        return NextResponse.next()
    }

    if (!req.auth) {
        return NextResponse.redirect(new URL("/login", baseUrl))
    }

    return NextResponse.next()
})

export const config = {
    matcher: ["/dashboard/:path*"]
}
