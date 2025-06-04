import { redis, incrementCounter } from "@/lib/redis";
import { NextResponse } from "next/server";

const DEBUG = false;
const MAX_ATTEMPTS = 12;
const WINDOW_TIME = 300;

export async function POST(req: Request) {
  try {
    const { ip, email } = await req.json();

    if (DEBUG) {
      return NextResponse.json({
        success: true,
        attempts: 0,
        remaining: MAX_ATTEMPTS,
      });
    }

    const ipKey = `ratelimit:login:ip:${ip}`;
    const emailKey = `ratelimit:login:email:${email}`;

    const ipAttempts = await incrementCounter(ipKey, WINDOW_TIME);
    const emailAttempts = await incrementCounter(emailKey, WINDOW_TIME);

    if (ipAttempts > MAX_ATTEMPTS || emailAttempts > MAX_ATTEMPTS) {
      return NextResponse.json(
        {
          error: "Too many login attempts. Please try again later.",
          blocked: true,
          remainingTime: WINDOW_TIME,
        },
        { status: 429 },
      );
    }

    return NextResponse.json({
      success: true,
      attempts: Math.max(ipAttempts, emailAttempts),
      remaining: MAX_ATTEMPTS - Math.max(ipAttempts, emailAttempts),
    });
  } catch (error) {
    console.error("Rate limit error:", error);
    return NextResponse.json({ success: true });
  }
}
