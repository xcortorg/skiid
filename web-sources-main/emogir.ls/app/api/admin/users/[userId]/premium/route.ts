import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { Session } from "next-auth";

const ADMIN_IDS = ["cm8a3itl40000vdtw948gpfp1", "cm8afkf1n000dpa7h6qhtr50v"];

export async function POST(
  req: Request,
  { params }: { params: Promise<{ userId: string }> },
) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { feature, until } = await req.json();
    const premiumUntil = new Date(until);

    const resolvedParams = await params;

    if (feature === "apiKeys") {
      return NextResponse.json(
        { error: "API access is managed separately" },
        { status: 400 },
      );
    }

    await db.user.update({
      where: { id: resolvedParams.userId },
      data: {
        isPremium: true,
        premiumUntil: premiumUntil,
        premiumType: "admin",
        features: {
          upsert: {
            create: {
              customDomain: true,
              imageHosting: true,
              maxLinks: 100,
              maxStorage: 1000,
              customThemes: true,
              removeWatermark: true,
              prioritySupport: true,
            },
            update: {
              customDomain: true,
              imageHosting: true,
              maxLinks: 100,
              maxStorage: 1000,
              customThemes: true,
              removeWatermark: true,
              prioritySupport: true,
            },
          },
        },
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Failed to update premium status:", error);
    return NextResponse.json(
      { error: "Failed to update premium status" },
      { status: 500 },
    );
  }
}
