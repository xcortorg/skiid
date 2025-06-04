import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { Session } from "next-auth";

export async function POST() {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    await db.user.update({
      where: { id: session.user.id },
      data: {
        twoFactorEnabled: false,
        twoFactorSecret: null,
        backupCodes: null,
        lastTwoFactorAt: null,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      {
        code: "50001",
        message: "Failed to disable 2FA",
        errors: [
          {
            code: "50001",
            message: "An unexpected error occurred",
            field: "server",
          },
        ],
      },
      { status: 500 },
    );
  }
}
