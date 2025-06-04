import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";

async function validateTurnstileToken(token: string) {
  try {
    console.log("TURNSTILE_VIEWS_KEY:", process.env.TURNSTILE_VIEWS_KEY);

    const response = await fetch(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          secret:
            process.env.TURNSTILE_VIEWS_KEY ||
            "1x0000000000000000000000000000000AA",
          response: token,
        }),
      }
    );

    const data = await response.json();
    console.log("Turnstile verification response:", data);
    return data.success;
  } catch (error) {
    console.error("Turnstile validation error:", error);
    return false;
  }
}

export async function POST(req: Request) {
  try {
    const { slug, token } = await req.json();
    const ip = req.headers.get("CF-Connecting-IP") || "unknown";

    if (!token) {
      return NextResponse.json({ error: "Token required" }, { status: 400 });
    }

    if (!ip || ip === "unknown") {
      return NextResponse.json({ error: "Invalid IP" }, { status: 400 });
    }

    const isValid = await validateTurnstileToken(token);
    if (!isValid) {
      return NextResponse.json({ error: "Invalid token" }, { status: 403 });
    }

    try {
      const pageView = await db.pageView.create({
        data: {
          slug,
          ip,
        },
      });
      return NextResponse.json({ success: true, pageView });
    } catch (error) {
      if (error instanceof Prisma.PrismaClientKnownRequestError) {
        if (error.code === "P2002") {
          return NextResponse.json(
            { error: "View already recorded for this IP" },
            { status: 409 }
          );
        }
      }
      throw error;
    }
  } catch (error) {
    console.error("View recording error:", error);
    return NextResponse.json(
      { error: "Failed to record view" },
      { status: 500 }
    );
  }
}
