import { NextResponse } from "next/server";
import { redis } from "@/lib/redis";
import { headers } from "next/headers";
import { db } from "@/lib/db";

export async function POST(req: Request) {
  try {
    const { email, code } = await req.json();
    const headersList = await headers();
    const ipAddress = headersList.get("x-forwarded-for") || "unknown";

    const user = await db.user.findUnique({
      where: { email },
      select: { id: true },
    });

    if (!user) {
      console.log("User not found for email:", email);
      return NextResponse.json(
        { error: "Invalid verification code" },
        { status: 400 },
      );
    }

    const storedCode = await redis.get(`verification:${user.id}:${ipAddress}`);

    console.log("Verification attempt:", {
      userId: user.id,
      ipAddress,
      expectedCode: storedCode,
      receivedCode: code,
      expectedType: typeof storedCode,
      receivedType: typeof code,
    });

    if (!storedCode || storedCode.toString() !== code) {
      return NextResponse.json(
        { error: "Invalid verification code" },
        { status: 400 },
      );
    }

    await redis.del(`verification:${user.id}:${ipAddress}`);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Verification error:", error);
    return NextResponse.json(
      { error: "Failed to verify code" },
      { status: 500 },
    );
  }
}
