import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { Resend } from "resend";
import { randomBytes } from "crypto";
import { redis, incrementCounter } from "@/lib/redis";
const resend = new Resend(process.env.RESEND_API_KEY);
const DEBUG = process.env.NODE_ENV === "development";
const MAX_ATTEMPTS = 3;
const WINDOW_TIME = 3600;

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
    const ipKey = `ratelimit:forgot:ip:${ip}`;
    const emailKey = `ratelimit:forgot:email:${email}`;

    const ipAttempts = await incrementCounter(ipKey, WINDOW_TIME);
    const emailAttempts = await incrementCounter(emailKey, WINDOW_TIME);
    const ttl = await redis.ttl(ipKey);

    if (ipAttempts > MAX_ATTEMPTS || emailAttempts > MAX_ATTEMPTS) {
      return {
        allowed: false,
        error: "Too many reset attempts. Please try again later.",
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

export async function POST(req: Request) {
  try {
    const ip =
      req.headers.get("x-forwarded-for")?.split(",")[0] ||
      req.headers.get("x-real-ip") ||
      "127.0.0.1";

    const { email, turnstileToken } = await req.json();

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

    const res = await fetch(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({
          secret: process.env.TURNSTILE_SECRET_KEY,
          response: turnstileToken,
        }),
      },
    );

    const data = await res.json();

    if (!data.success) {
      return NextResponse.json(
        { error: "Invalid security check" },
        { status: 400 },
      );
    }

    const user = await db.user.findUnique({
      where: { email },
    });

    if (!user) {
      return NextResponse.json({
        message: "If an account exists, you will receive an email shortly",
      });
    }

    const token = randomBytes(32).toString("hex");
    const expires = new Date(Date.now() + 3600000);

    await db.user.update({
      where: { id: user.id },
      data: {
        resetToken: token,
        resetTokenExpires: expires,
      },
    });

    const resetLink = `${process.env.NEXTAUTH_URL}/reset-password?token=${token}`;

    await resend.emails.send({
      from: "Emogir.ls <noreply@emogir.ls>",
      to: email,
      subject: "Reset your password",
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta content="width=device-width" name="viewport" />
            <meta content="text/html; charset=UTF-8" http-equiv="Content-Type" />
            <title>Reset your password</title>
          </head>
          <body style="background-color: #0f0a14; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;">
            <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="max-width: 600px; width: 100%; margin: 0 auto;">
              <tr>
                <td style="padding: 40px 20px;">
                  <div style="background: linear-gradient(180deg, #231623 0%, #1a121a 100%); border-radius: 16px; padding: 40px; margin-bottom: 30px; border: 1px solid #4a2a4a;">
                    <h1 style="margin: 0 0 20px 0; font-size: 24px; color: #ffffff; text-align: center;">
                      Reset Your Password
                    </h1>
                    
                    <p style="margin: 0 0 20px 0; line-height: 1.6; color: #a67ba6; text-align: center;">
                      We received a request to reset your password. Click the button below to choose a new password. 
                      If you didn't request this, you can safely ignore this email.
                    </p>

                    <div style="text-align: center; margin-bottom: 30px;">
                      <a href="${resetLink}" style="display: inline-block; padding: 15px 30px; background: linear-gradient(45deg, #ff3379, #ff6b6b); border-radius: 8px; color: white; text-decoration: none; font-weight: 500;">
                        Reset Password
                      </a>
                    </div>

                    <p style="margin: 0 0 10px 0; color: #a67ba6; font-size: 14px; text-align: center;">
                      This link will expire in 1 hour for security reasons.
                    </p>

                    <p style="margin: 0; color: #a67ba6; font-size: 14px; text-align: center;">
                      If the button doesn't work, copy and paste this link:<br/>
                      <a href="${resetLink}" style="color: #ff3379; text-decoration: none; word-break: break-all;">
                        ${resetLink}
                      </a>
                    </p>
                  </div>

                  <div style="text-align: center;">
                    <p style="margin: 0; color: #a67ba6; font-size: 12px;">
                      © 2025 Emogir.ls. All rights reserved.
                    </p>
                  </div>
                </td>
              </tr>
            </table>
          </body>
        </html>
      `,
    });

    return NextResponse.json({
      message: "If an account exists, you will receive an email shortly",
    });
  } catch (error) {
    console.error("Password reset error:", error);
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 },
    );
  }
}
