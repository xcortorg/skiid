import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { Session } from "next-auth";

export async function GET() {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const user = await db.user.findUnique({
      where: { id: session.user.id },
      select: { backupCodes: true },
    });

    if (!user?.backupCodes) {
      return NextResponse.json({ backupCodes: [] });
    }

    return NextResponse.json({
      backupCodes: JSON.parse(user.backupCodes),
    });
  } catch (error) {
    return NextResponse.json(
      {
        code: "50001",
        message: "Failed to fetch backup codes",
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
