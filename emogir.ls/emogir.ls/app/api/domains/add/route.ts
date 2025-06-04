import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { Session } from "next-auth";

export async function POST(request: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;

    if (!session?.user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { subdomain, domain } = body;

    if (!subdomain || !domain) {
      return NextResponse.json(
        { error: "Missing subdomain or domain" },
        { status: 400 },
      );
    }

    const existingDomains = await db.imageHostDomain.count({
      where: { userId: session.user.id },
    });

    if (existingDomains >= 3) {
      return NextResponse.json(
        { error: "Maximum domain limit reached" },
        { status: 400 },
      );
    }

    const domainExists = await db.imageHostDomain.findFirst({
      where: { subdomain, domain },
    });

    if (domainExists) {
      return NextResponse.json(
        { error: "Domain already taken" },
        { status: 400 },
      );
    }

    const newDomain = await db.imageHostDomain.create({
      data: {
        userId: session.user.id,
        subdomain,
        domain,
      },
    });

    return NextResponse.json(newDomain);
  } catch (error) {
    console.error("Failed to add domain:", error);
    return NextResponse.json(
      { error: "Failed to add domain" },
      { status: 500 },
    );
  }
}
