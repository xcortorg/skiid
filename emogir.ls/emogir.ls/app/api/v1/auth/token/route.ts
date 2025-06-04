import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import crypto from "crypto";
import { Session } from "next-auth";

export async function POST(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const { name } = body;

    if (!name || typeof name !== "string") {
      return NextResponse.json(
        { error: "Token name is required" },
        { status: 400 },
      );
    }

    const tokenValue = crypto.randomBytes(32).toString("hex");
    const hashedToken = crypto
      .createHash("sha256")
      .update(tokenValue)
      .digest("hex");

    const token = await db.apiToken.create({
      data: {
        userId: session.user.id,
        name,
        token: hashedToken,
        rateLimit: 100,
        expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
      },
    });

    return NextResponse.json({
      id: token.id,
      name: token.name,
      token: tokenValue,
      rateLimit: token.rateLimit,
      expiresAt: token.expiresAt,
      message: "Store this token securely. It won't be shown again.",
    });
  } catch (error) {
    console.error("Token creation error:", error);
    return NextResponse.json(
      { error: "Failed to create token" },
      { status: 500 },
    );
  }
}

export async function GET(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const user = await db.user.findUnique({
      where: { id: session.user.id },
      select: {
        apiKeysEnabled: true,
        maxApiKeys: true,
        apiTokens: {
          where: { isActive: true },
          select: {
            id: true,
            name: true,
            lastUsed: true,
            createdAt: true,
            expiresAt: true,
            rateLimit: true,
          },
        },
      },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    return NextResponse.json({
      apiEnabled: user.apiKeysEnabled,
      maxKeys: user.maxApiKeys,
      tokens: user.apiTokens,
    });
  } catch (error) {
    console.error("Token fetch error:", error);
    return NextResponse.json(
      { error: "Failed to fetch tokens" },
      { status: 500 },
    );
  }
}
