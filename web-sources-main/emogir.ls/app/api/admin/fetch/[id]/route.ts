import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { Session } from "next-auth";

const ADMIN_IDS = ["cm8a3itl40000vdtw948gpfp1", "cm8afkf1n000dpa7h6qhtr50v"];

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;
  if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const resolvedParams = await params;
  const user = await db.user.findUnique({
    where: { id: resolvedParams.id },
    include: {
      features: true,
      links: true,
      sessions: true,
      inviteUsed: true,
      createdInvites: true,
      uploads: true,
    },
  });

  if (!user) {
    return new NextResponse("Not found", { status: 404 });
  }

  return NextResponse.json(user);
}
