import { registerUser } from "@/lib/auth";
import { NextRequest, NextResponse } from "next/server";
import { redis, incrementCounter } from "@/lib/redis";
import { db } from "@/lib/db";
import { withMetrics } from "@/lib/api-wrapper";

const DEBUG = process.env.NODE_ENV === "development";
const MAX_ATTEMPTS = 3;
const WINDOW_TIME = 3600;
const MAX_ACCOUNTS_PER_IP = 2;
const IP_ACCOUNT_WINDOW = 86400;

async function checkRateLimit(
  ip: string,
  email: string,
): Promise<{
  allowed: boolean;
  error?: string;
  remainingTime?: number;
}> {
  if (DEBUG) return { allowed: true };

  try {
    const ipKey = `ratelimit:register:ip:${ip}`;
    const emailKey = `ratelimit:register:email:${email}`;
    const ipAccountKey = `register:ip:count:${ip}`;

    const accountsFromIp = await redis.scard(`register:ip:${ip}`);
    if (accountsFromIp >= MAX_ACCOUNTS_PER_IP) {
      const ttl = await redis.ttl(ipAccountKey);
      return {
        allowed: false,
        error: "Maximum number of accounts created from this IP",
        remainingTime: ttl > 0 ? ttl : IP_ACCOUNT_WINDOW,
      };
    }

    const ipAttempts = await incrementCounter(ipKey, WINDOW_TIME);
    const emailAttempts = await incrementCounter(emailKey, WINDOW_TIME);
    const ttl = await redis.ttl(ipKey);

    if (ipAttempts > MAX_ATTEMPTS || emailAttempts > MAX_ATTEMPTS) {
      return {
        allowed: false,
        error: "Too many registration attempts. Please try again later.",
        remainingTime: ttl > 0 ? ttl : WINDOW_TIME,
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

async function handlePOST(req: Request) {
  const nextReq = req as unknown as NextRequest;

  try {
    const ip =
      nextReq.headers.get("x-forwarded-for")?.split(",")[0] ||
      nextReq.headers.get("x-real-ip") ||
      "127.0.0.1";

    const body = await nextReq.json();
    const { verificationCode, email, password, slug, displayName, inviteCode } =
      body;

    if (!email || !password || !slug || !inviteCode) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 },
      );
    }

    if (slug.length < 4) {
      return NextResponse.json(
        {
          error:
            "Username too short. Please contact support for usernames shorter than 4 characters.",
        },
        { status: 400 },
      );
    }

    if (!DEBUG) {
      const rateLimitCheck = await checkRateLimit(ip, email);
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
    }

    if (password.length < 8) {
      return NextResponse.json(
        { error: "Password must be at least 8 characters long" },
        { status: 400 },
      );
    }

    if (!/^[a-z0-9-]+$/.test(slug)) {
      return NextResponse.json(
        {
          error:
            "Slug can only contain lowercase letters, numbers, and hyphens",
        },
        { status: 400 },
      );
    }

    if (DEBUG) {
      console.log("Verification attempt:", {
        stored: await redis.get(`verify:${email}`),
        received: verificationCode,
        email,
      });
    }

    const storedData = (await redis.get(`verify:${email}`)) as {
      code: string;
      inviteCode: string;
    };
    if (!storedData) {
      return NextResponse.json(
        { error: "Invalid or expired verification code" },
        { status: 400 },
      );
    }

    const { code: storedCode, inviteCode: storedInviteCode } = storedData;

    if (
      String(storedCode) !== String(verificationCode) ||
      storedInviteCode !== inviteCode
    ) {
      return NextResponse.json(
        { error: "Invalid or expired verification code" },
        { status: 400 },
      );
    }

    const inviteCodeRecord = await db.inviteCode.findFirst({
      where: {
        code: inviteCode,
        userId: null,
      },
    });

    if (!inviteCodeRecord) {
      return NextResponse.json(
        { error: "Invalid or already used invite code" },
        { status: 400 },
      );
    }

    await redis.del(`verify:${email}`);

    await redis.sadd(`register:ip:${ip}`, email);
    await redis.expire(`register:ip:${ip}`, IP_ACCOUNT_WINDOW);

    const user = await registerUser({
      email,
      password,
      slug,
      displayName,
    });

    await db.inviteCode.update({
      where: { id: inviteCodeRecord.id },
      data: {
        usedAt: new Date(),
        userId: user.id,
        usedBy: {
          connect: { id: user.id },
        },
      },
    });

    return NextResponse.json({
      user: {
        id: user.id,
        email: user.email,
        username: user.username,
        name: user.name,
      },
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
}

export const POST = withMetrics(handlePOST);
