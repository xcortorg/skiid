import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { getCustomHostname, findHostnameIdentifier } from "@/lib/cloudflare";
import { Session } from "next-auth";

export async function GET(req: Request) {
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

    const url = new URL(req.url);
    const hostname = url.searchParams.get("hostname");

    if (!hostname) {
      return NextResponse.json(
        { error: "Hostname parameter is required" },
        { status: 400 },
      );
    }

    const hostnameId =
      user.customHostnameId || (await findHostnameIdentifier(hostname));

    if (!hostnameId) {
      return NextResponse.json({
        verified: false,
        message: "Domain not found. Please verify your domain first.",
      });
    }

    const customHostname = await getCustomHostname(hostnameId);

    const isVerified =
      customHostname.status === "active" &&
      customHostname.ssl?.status === "active";

    if (isVerified) {
      return NextResponse.json({
        verified: true,
        message: "Domain is verified and active",
        status: customHostname.status,
        ssl: customHostname.ssl?.status,
      });
    } else if (customHostname.verification_errors?.length) {
      return NextResponse.json({
        verified: false,
        message: "Domain verification failed",
        errors: customHostname.verification_errors,
        status: customHostname.status,
      });
    } else {
      return NextResponse.json({
        verified: false,
        message:
          "Domain verification in progress. This may take up to 24 hours.",
        status: customHostname.status,
        ssl: customHostname.ssl?.status,
      });
    }
  } catch (error) {
    console.error("Error checking domain status:", error);
    return NextResponse.json(
      { error: "Failed to check domain status" },
      { status: 500 },
    );
  }
}
