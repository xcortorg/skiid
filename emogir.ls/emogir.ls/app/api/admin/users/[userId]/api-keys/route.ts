import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { Session } from "next-auth";

const ADMIN_IDS = ["cm8a3itl40000vdtw948gpfp1", "cm8afkf1n000dpa7h6qhtr50v"];

export async function POST(
  req: Request,
  { params }: { params: Promise<{ userId: string }> },
): Promise<Response> {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const resolvedParams = await params;
    const body = await req.json();
    const { maxKeys } = body;

    if (typeof maxKeys !== "number" || maxKeys < 0 || maxKeys > 10) {
      return NextResponse.json(
        { error: "Invalid key limit. Must be between 0 and 10" },
        { status: 400 },
      );
    }

    const user = await db.user.findUnique({
      where: { id: resolvedParams.userId },
      select: { id: true },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    await db.user.update({
      where: { id: resolvedParams.userId },
      data: {
        apiKeysEnabled: maxKeys > 0,
        maxApiKeys: maxKeys,
      },
    });

    return NextResponse.json({
      success: true,
      message: `API keys ${maxKeys > 0 ? "enabled" : "disabled"} for user`,
      maxKeys,
    });
  } catch (error) {
    console.error("API key update error:", error);
    return NextResponse.json(
      { error: "Failed to update API key settings" },
      { status: 500 },
    );
  }
}
