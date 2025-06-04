import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { authenticator } from "otplib";
import { redis, incrementCounter } from "@/lib/redis";
import { verifyBackupCode } from "@/lib/2fa";
import { Session } from "next-auth";

const MAX_ATTEMPTS = 5;
const WINDOW_TIME = 300;

async function checkRateLimit(userId: string): Promise<{
  allowed: boolean;
  error?: string;
  remainingTime?: number;
}> {
  try {
    const key = `ratelimit:2fa-verify:user:${userId}`;
    const attempts = await incrementCounter(key, WINDOW_TIME);

    if (attempts > MAX_ATTEMPTS) {
      return {
        allowed: false,
        error: "Too many verification attempts. Please try again later.",
        remainingTime: WINDOW_TIME,
      };
    }

    return { allowed: true };
  } catch (error) {
    console.error("Rate limit error:", error);
    return {
      allowed: false,
      error: "Service temporarily unavailable",
    };
  }
}

export async function POST(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const rateLimitCheck = await checkRateLimit(session.user.id);
    if (!rateLimitCheck.allowed) {
      return NextResponse.json(
        {
          error: rateLimitCheck.error,
          blocked: true,
          remainingTime: rateLimitCheck.remainingTime,
        },
        { status: 429 },
      );
    }

    const { code } = await req.json();
    console.log("Attempting 2FA verification with code:", code);

    const user = await db.user.findUnique({
      where: { id: session.user.id },
      select: {
        twoFactorSecret: true,
        backupCodes: true,
      },
    });
    console.log("User 2FA data:", {
      hasSecret: !!user?.twoFactorSecret,
      hasBackupCodes: !!user?.backupCodes,
      backupCodes: user?.backupCodes ? JSON.parse(user.backupCodes) : null,
    });

    if (!user?.twoFactorSecret) {
      return NextResponse.json(
        {
          code: "40001",
          message: "2FA not setup",
          errors: [
            {
              code: "40001",
              message: "2FA has not been setup for this account",
              field: "setup",
            },
          ],
        },
        { status: 400 },
      );
    }

    const isValid = authenticator.verify({
      token: code,
      secret: user.twoFactorSecret,
    });
    console.log("TOTP verification result:", isValid);

    if (!isValid && user.backupCodes) {
      const isValidBackup = verifyBackupCode(code, user.backupCodes);
      console.log("Backup code verification result:", isValidBackup);
      if (isValidBackup) {
        await db.user.update({
          where: { id: session.user.id },
          data: {
            twoFactorEnabled: true,
            lastTwoFactorAt: new Date(),
            backupCodes: JSON.parse(user.backupCodes).filter(
              (c: string) => c !== code,
            ),
          },
        });

        const key = `ratelimit:2fa-verify:user:${session.user.id}`;
        await redis.del(key);

        return NextResponse.json({ success: true });
      }
    }

    if (!isValid) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Invalid code",
          errors: [
            {
              code: "40002",
              message: "The verification code is invalid",
              field: "code",
            },
          ],
        },
        { status: 400 },
      );
    }

    await db.user.update({
      where: { id: session.user.id },
      data: {
        twoFactorEnabled: true,
        lastTwoFactorAt: new Date(),
      },
    });

    const key = `ratelimit:2fa-verify:user:${session.user.id}`;
    await redis.del(key);

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      {
        code: "50001",
        message: "Failed to verify 2FA",
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
