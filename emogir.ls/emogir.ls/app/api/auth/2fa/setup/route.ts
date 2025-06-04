import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { authenticator } from "otplib";
import crypto from "crypto";
import { Session } from "next-auth";

function generateBackupCode() {
  return Array.from({ length: 3 }, () =>
    crypto.randomBytes(2).toString("hex").toUpperCase(),
  ).join("-");
}

export async function POST() {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const secret = authenticator.generateSecret();

    const backupCodes = Array.from({ length: 8 }, generateBackupCode);

    await db.user.update({
      where: { id: session.user.id },
      data: {
        twoFactorSecret: secret,
        backupCodes: JSON.stringify(backupCodes),
      },
    });

    return NextResponse.json({
      secret,
      backupCodes,
    });
  } catch (error) {
    return NextResponse.json(
      {
        code: "50001",
        message: "Failed to setup 2FA",
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
