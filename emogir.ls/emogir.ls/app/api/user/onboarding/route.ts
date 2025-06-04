import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { Session } from "next-auth";

export async function POST() {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;

    if (!session?.user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    await db.user.update({
      where: { email: session.user.email },
      data: { onboarding: true },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Onboarding update error:", error);
    return NextResponse.json(
      { error: "Failed to update onboarding status" },
      { status: 500 },
    );
  }
}
