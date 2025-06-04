import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import bcrypt from "bcryptjs";
import { redis, incrementCounter } from "@/lib/redis";
import { Session } from "next-auth";

const MAX_ATTEMPTS = 5;
const WINDOW_TIME = 900;

async function checkRateLimit(userId: string): Promise<{
  allowed: boolean;
  error?: string;
  remainingTime?: number;
}> {
  try {
    const key = `ratelimit:change-password:user:${userId}`;
    const attempts = await incrementCounter(key, WINDOW_TIME);

    if (attempts > MAX_ATTEMPTS) {
      return {
        allowed: false,
        error: "Too many password change attempts. Please try again later.",
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

    const { currentPassword, newPassword, code } = await req.json();

    const user = await db.user.findUnique({
      where: { id: session.user.id },
      select: {
        password: true,
        twoFactorEnabled: true,
        twoFactorSecret: true,
      },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    const isValid = await bcrypt.compare(currentPassword, user.password);
    if (!isValid) {
      return NextResponse.json(
        { error: "Invalid current password" },
        { status: 400 },
      );
    }

    if (user.twoFactorEnabled) {
      if (!code) {
        return NextResponse.json({ error: "2FA_REQUIRED" }, { status: 400 });
      }

      const { authenticator } = await import("otplib");
      const isValidCode = authenticator.verify({
        token: code,
        secret: user.twoFactorSecret!,
      });

      if (!isValidCode) {
        return NextResponse.json(
          { error: "Invalid 2FA code" },
          { status: 400 },
        );
      }
    }

    const hashedPassword = await bcrypt.hash(newPassword, 12);
    await db.user.update({
      where: { id: session.user.id },
      data: { password: hashedPassword },
    });

    const key = `ratelimit:change-password:user:${session.user.id}`;
    await redis.del(key);

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
