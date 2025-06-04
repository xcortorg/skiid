import { redis, incrementCounter } from "@/lib/redis";
import { NextResponse } from "next/server";
import { Resend } from "resend";
import { verifyTurnstileToken } from "@/lib/turnstile";
import { db } from "@/lib/db";

const resend = new Resend(process.env.RESEND_API_KEY);
const MAX_ATTEMPTS = 3;
const WINDOW_TIME = 900;
const CODE_EXPIRY = 600;
const DEBUG_KEY = process.env.DEBUG_KEY;

const emailTemplate = (code: string) => `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify your email</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      margin: 0;
      padding: 0;
      background: #0a0a0a;
      color: #ffffff;
    }
    h1 {
      color: #ffffff;
    }
    p {
      color: #ffffff;
    }
    .container {
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
    }
    .card {
      background: #1a1a1a;
      border-radius: 12px;
      padding: 32px;
      margin: 20px 0;
      border: 1px solid #333;
    }
    .logo {
      font-size: 24px;
      font-weight: bold;
      margin-bottom: 24px;
    }
    .pink {
      color: #ff3379;
    }
    .code {
      font-family: monospace;
      font-size: 32px;
      color: #ffffff;
      letter-spacing: 4px;
      background: #2a2a2a;
      padding: 16px 24px;
      border-radius: 8px;
      margin: 24px 0;
      text-align: center;
    }
    .footer {
      font-size: 14px;
      color: #ffffff;
      text-align: center;
      margin-top: 24px;
    }
    .note {
      font-size: 14px;
      color: #ffffff;
      margin-top: 16px;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <div class="logo">
        emogir<span class="pink">.ls</span>
      </div>
      
      <h1>Verify your email</h1>
      <p>Enter this verification code to continue with your registration:</p>
      
      <div class="code">${code}</div>
      
      <p class="note">This code will expire in 10 minutes.</p>
      
      <div class="footer">
        If you didn't request this code, you can safely ignore this email.
      </div>
    </div>
  </div>
</body>
</html>
`;

async function generateVerificationCode(): Promise<string> {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

async function checkRateLimit(email: string): Promise<{
  allowed: boolean;
  error?: string;
  remainingTime?: number;
}> {
  try {
    const key = `ratelimit:email-verify:${email}`;
    const attempts = await incrementCounter(key, WINDOW_TIME);
    const ttl = await redis.ttl(key);

    if (attempts > MAX_ATTEMPTS) {
      return {
        allowed: false,
        error: "Too many verification attempts. Please try again later.",
        remainingTime: ttl,
      };
    }

    return {
      allowed: true,
      remainingTime: WINDOW_TIME - ttl,
    };
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
    const { email, turnstileToken, debugKey, inviteCode } = await req.json();

    const isDebugMode =
      debugKey === DEBUG_KEY && process.env.NODE_ENV === "development";

    if (!email || !turnstileToken || !inviteCode) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 },
      );
    }

    const invite = await db.inviteCode.findFirst({
      where: {
        code: inviteCode,
        userId: null,
      },
    });

    if (!invite) {
      return NextResponse.json(
        { error: "Invalid or already used invite code" },
        { status: 400 },
      );
    }

    const isValidToken = await verifyTurnstileToken(turnstileToken);
    if (!isValidToken) {
      return NextResponse.json(
        { error: "Invalid challenge response" },
        { status: 400 },
      );
    }

    if (!isDebugMode) {
      const rateLimitCheck = await checkRateLimit(email);
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

    const code = await generateVerificationCode();
    await redis.set(
      `verify:${email}`,
      JSON.stringify({
        code,
        inviteCode,
      }),
      { ex: CODE_EXPIRY },
    );

    await resend.emails.send({
      from: "verify@emogir.ls",
      to: email,
      subject: "Verify your email",
      html: emailTemplate(code),
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Email verification error:", error);
    return NextResponse.json(
      { error: "Failed to send verification email" },
      { status: 500 },
    );
  }
}
