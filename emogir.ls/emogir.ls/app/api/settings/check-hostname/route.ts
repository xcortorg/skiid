import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { Session } from "next-auth";

export async function GET(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;

    if (!session?.user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const user = await db.user.findUnique({
      where: { email: session.user.email },
      include: { features: true },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    const isPremiumActive =
      user.isPremium &&
      (!user.premiumUntil || new Date(user.premiumUntil) > new Date());

    if (!isPremiumActive || !user.features?.customDomain) {
      return NextResponse.json(
        { error: "Premium subscription required for custom domains" },
        { status: 403 },
      );
    }

    const url = new URL(req.url);
    const hostname = url.searchParams.get("hostname");

    if (!hostname) {
      return NextResponse.json(
        { error: "Hostname parameter is required" },
        { status: 400 },
      );
    }

    const hostnameRegex =
      /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/;
    if (!hostnameRegex.test(hostname)) {
      return NextResponse.json(
        { error: "Invalid hostname format", available: false },
        { status: 400 },
      );
    }

    const existingUser = await db.user.findFirst({
      where: {
        customHostname: hostname,
        email: { not: session.user.email },
      },
    });

    return NextResponse.json({
      available: !existingUser,
      message: existingUser
        ? "This hostname is already in use"
        : "Hostname is available",
    });
  } catch (error) {
    console.error("Error checking hostname availability:", error);
    return NextResponse.json(
      { error: "Failed to check hostname availability" },
      { status: 500 },
    );
  }
}
