import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const ADMIN_IDS = ["cm8a3itl40000vdtw948gpfp1"];

async function handleDiscordVerification(request: NextRequest) {
  try {
    const protocol = request.headers.get("x-forwarded-proto") || "http";
    const host = request.headers.get("host");
    const url = `${protocol}://${host}/api/discord-verification`;

    const response = await fetch(url, {
      headers: request.headers,
    });

    if (!response.ok) throw new Error("File not found");

    const content = await response.text();

    return new NextResponse(content, {
      status: 200,
      headers: {
        "Content-Type": "text/plain",
      },
    });
  } catch (error) {
    console.error("Error serving file:", error);
    return new NextResponse("Not Found", { status: 404 });
  }
}

const withAuthMiddleware = withAuth(
  function middleware(req) {
    if (req.nextUrl.pathname.startsWith("/dashboard") && !req.nextauth.token) {
      return NextResponse.redirect(new URL("/login", req.url));
    }

    if (
      req.nextUrl.pathname.startsWith("/admin") &&
      (!req.nextauth.token?.sub || !ADMIN_IDS.includes(req.nextauth.token.sub))
    ) {
      return NextResponse.redirect(new URL("/", req.url));
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token }) => !!token,
    },
  },
);

export function middleware(req: NextRequest) {
  if (req.nextUrl.pathname === "/api/metrics") {
    return NextResponse.next();
  }

  if (req.nextUrl.pathname.startsWith("/api")) {
    const response = NextResponse.next();
    response.headers.set("x-request-start", Date.now().toString());
    return response;
  }

  if (req.nextUrl.pathname === "/.well-known/discord") {
    return handleDiscordVerification(req);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/api/metrics",
    "/api/:path*",
    "/.well-known/:path*",
    "/dashboard/:path*",
    "/admin/:path*",
  ],
};
