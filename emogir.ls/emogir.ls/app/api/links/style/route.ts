import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { Session } from "next-auth";

export async function GET(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const linkStyle = await db.link.findFirst({
      where: { userId: session.user.id },
      select: {
        backgroundColor: true,
        hoverColor: true,
        borderColor: true,
        gap: true,
        primaryTextColor: true,
        secondaryTextColor: true,
        hoverTextColor: true,
        textSize: true,
        iconSize: true,
        iconColor: true,
        iconBgColor: true,
        iconBorderRadius: true,
      },
    });

    const appearance = await db.appearance.findUnique({
      where: { userId: session.user.id },
      select: {
        linksCompactMode: true,
      },
    });

    return NextResponse.json({
      ...linkStyle,
      compactMode: appearance?.linksCompactMode ?? false,
    });
  } catch (error) {
    console.error("Error fetching link styles:", error);
    return NextResponse.json(
      { error: "Failed to fetch link styles" },
      { status: 500 },
    );
  }
}

export async function PUT(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const data = await req.json();

    console.log("Received link style data:", data);

    await db.link.updateMany({
      where: { userId: session.user.id },
      data: {
        backgroundColor: data.backgroundColor,
        hoverColor: data.hoverColor,
        borderColor: data.borderColor,
        gap: data.gap,
        primaryTextColor: data.primaryTextColor,
        secondaryTextColor: data.secondaryTextColor,
        hoverTextColor: data.hoverTextColor,
        textSize: data.textSize,
        iconSize: data.iconSize,
        iconColor: data.iconColor,
        iconBgColor: data.iconBgColor,
        iconBorderRadius: data.iconBorderRadius,
      },
    });

    await db.appearance.update({
      where: { userId: session.user.id },
      data: {
        linksCompactMode: data.compactMode,
        linksIconBgEnabled: data.iconBgEnabled,
        linksDisableBackground: data.disableBackground ?? false,
        linksDisableHover: data.disableHover ?? false,
        linksDisableBorder: data.disableBorder ?? false,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error updating link styles:", error);
    return NextResponse.json(
      { error: "Failed to update link styles" },
      { status: 500 },
    );
  }
}
