import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { Session } from "next-auth";

const ADMIN_IDS = ["cm8a3itl40000vdtw948gpfp1", "cm8afkf1n000dpa7h6qhtr50v"];

export async function POST(
  req: Request,
  { params }: { params: Promise<{ userId: string }> },
) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const resolvedParams = await params;
    await db.user.update({
      where: { id: resolvedParams.userId },
      data: {
        isDisabled: true,
        sessions: {
          updateMany: {
            where: { isActive: true },
            data: { isActive: false },
          },
        },
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Failed to disable user:", error);
    return NextResponse.json(
      { error: "Failed to disable user" },
      { status: 500 },
    );
  }
}
