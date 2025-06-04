import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> },
) {
  try {
    const resolvedParams = await params;
    const account = await db.account.findFirst({
      where: {
        userId: resolvedParams.userId,
        provider: "discord",
      },
    });

    if (!account) {
      return NextResponse.json(null);
    }

    const response = await fetch("https://discord.com/api/users/@me", {
      headers: { Authorization: `Bearer ${account.access_token}` },
    });

    if (!response.ok) {
      return NextResponse.json(null);
    }

    const discordUser = await response.json();
    return NextResponse.json({
      id: discordUser.id,
      username: discordUser.username,
      discriminator: discordUser.discriminator,
    });
  } catch (error) {
    console.error("Error fetching Discord account:", error);
    return NextResponse.json(null);
  }
}
