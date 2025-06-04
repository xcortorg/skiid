import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { Session } from "next-auth";

export async function GET() {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const account = await db.account.findFirst({
      where: {
        userId: session.user.id,
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

export async function DELETE() {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    await db.account.deleteMany({
      where: {
        userId: session.user.id,
        provider: "discord",
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error disconnecting Discord:", error);
    return NextResponse.json(
      { error: "Failed to disconnect" },
      { status: 500 },
    );
  }
}
