import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { randomBytes } from "crypto";
import { Session } from "next-auth";

const generateAuthKey = () => {
  return randomBytes(32).toString("hex");
};

export async function POST(request: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;

    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { subdomain, domain } = await request.json();

    const existingDomain = await db.imageHostDomain.findFirst({
      where: {
        subdomain,
        domain,
      },
    });

    if (existingDomain) {
      return NextResponse.json(
        { error: "Domain already exists" },
        { status: 400 },
      );
    }

    const domainCount = await db.imageHostDomain.count({
      where: {
        userId: session.user.id,
      },
    });

    if (domainCount >= 3) {
      return NextResponse.json(
        { error: "Maximum domains reached (3)" },
        { status: 400 },
      );
    }

    const newDomain = await db.imageHostDomain.create({
      data: {
        userId: session.user.id,
        subdomain,
        domain,
        authorization: generateAuthKey(),
        oembed: {
          title: "",
          description: "",
          color: "#ff3379",
          siteName: "",
          showMetadata: true,
        },
      },
    });

    return NextResponse.json(newDomain);
  } catch (error) {
    console.error("Failed to create domain:", error);
    return NextResponse.json(
      { error: "Failed to create domain" },
      { status: 500 },
    );
  }
}

export async function PUT(req: Request) {
  try {
    const {
      domainId,
      embedTitle,
      embedDescription,
      embedColor,
      embedSiteName,
      embedAuthorName,
      embedAuthorUrl,
      showMetadata,
    } = await req.json();

    const domain = await db.imageHostDomain.findFirst({
      where: { id: domainId },
    });

    if (!domain) {
      return NextResponse.json({ error: "Domain not found" }, { status: 404 });
    }

    const updatedDomain = await db.imageHostDomain.update({
      where: { id: domainId },
      data: {
        oembed: {
          type: "photo",
          version: "1.0",
          title: embedTitle,
          description: embedDescription,
          provider_name: embedSiteName,
          provider_url: `https://${domain.subdomain}.${domain.domain}`,
          author_name: embedAuthorName,
          author_url: embedAuthorUrl,
          color: embedColor,
          showMetadata: showMetadata,
        },
      },
    });

    return NextResponse.json(updatedDomain);
  } catch (error) {
    console.error("Failed to update domain settings:", error);
    return NextResponse.json(
      { error: "Failed to update settings" },
      { status: 500 },
    );
  }
}
