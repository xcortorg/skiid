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

  const sessions = await db.session.findMany({
    where: {
      userId: session.user.id,
      isActive: true,
    },
    orderBy: {
      lastActive: "desc",
    },
  });

  return NextResponse.json(sessions);
}

export async function DELETE(req: Request) {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const sessionId = searchParams.get("id");

  if (!sessionId) {
    return NextResponse.json({ error: "Session ID required" }, { status: 400 });
  }

  await db.session.update({
    where: {
      id: sessionId,
      userId: session.user.id,
    },
    data: {
      isActive: false,
    },
  });

  return NextResponse.json({ success: true });
}
