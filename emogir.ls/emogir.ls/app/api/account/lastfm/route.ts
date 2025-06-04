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
        provider: "lastfm",
      },
    });

    if (!account) {
      return NextResponse.json(null);
    }

    return NextResponse.json({
      username: account.providerAccountId,
      url: `https://www.last.fm/user/${account.providerAccountId}`,
    });
  } catch (error) {
    console.error("Error fetching Last.fm account:", error);
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
        provider: "lastfm",
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error disconnecting Last.fm:", error);
    return NextResponse.json(
      { error: "Failed to disconnect" },
      { status: 500 },
    );
  }
}
