import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { Session } from "next-auth";

export async function GET() {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;

    if (!session?.user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const user = await db.user.findUnique({
      where: { email: session.user.email },
      include: {
        features: true,
      },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    return NextResponse.json({
      isPremium:
        user.isPremium &&
        (!user.premiumUntil || new Date(user.premiumUntil) > new Date()),
      features: user.features || {
        imageHosting: false,
      },
    });
  } catch (error) {
    console.error("Premium status fetch error:", error);
    return NextResponse.json(
      { error: "Failed to fetch premium status" },
      { status: 500 },
    );
  }
}
