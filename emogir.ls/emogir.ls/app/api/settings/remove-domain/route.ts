import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { deleteCustomHostname } from "@/lib/cloudflare";
import { Session } from "next-auth";

export async function POST(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;

    if (!session?.user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const user = await db.user.findUnique({
      where: { email: session.user.email },
      include: { features: true },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    const isPremiumActive =
      user.isPremium &&
      (!user.premiumUntil || new Date(user.premiumUntil) > new Date());

    if (!isPremiumActive || !user.features?.customDomain) {
      return NextResponse.json(
        { error: "Premium subscription required for custom domains" },
        { status: 403 },
      );
    }

    const { hostname } = await req.json();

    if (!hostname) {
      return NextResponse.json(
        { error: "Hostname is required" },
        { status: 400 },
      );
    }

    if (user.customHostnameId) {
      try {
        await deleteCustomHostname(user.customHostnameId);
      } catch (error) {
        console.error("Error deleting hostname from Cloudflare:", error);
      }
    }

    await db.user.update({
      where: { id: user.id },
      data: {
        customHostname: null,
        customHostnameId: null,
      },
    });

    return NextResponse.json({
      success: true,
      message: "Custom domain removed successfully",
    });
  } catch (error) {
    console.error("Error removing domain:", error);
    return NextResponse.json(
      { error: "Failed to remove domain" },
      { status: 500 },
    );
  }
}
