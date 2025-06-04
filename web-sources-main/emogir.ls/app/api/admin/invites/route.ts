import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { nanoid } from "nanoid";
import { withMetrics } from "@/lib/api-wrapper";
import { Session } from "next-auth";

const ADMIN_IDS = ["cm8a3itl40000vdtw948gpfp1", "cm8afkf1n000dpa7h6qhtr50v"];

export async function POST() {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;
  if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const code = nanoid(8);

    const inviteCode = await db.inviteCode.create({
      data: {
        code,
        creatorId: session.user.id,
      },
    });

    return NextResponse.json(inviteCode);
  } catch (error) {
    console.error("Error creating invite code:", error);
    return NextResponse.json(
      { error: "Failed to create invite code" },
      { status: 500 },
    );
  }
}

async function handleGET(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const inviteCodes = await db.inviteCode.findMany({
      include: {
        usedBy: {
          select: {
            id: true,
            username: true,
          },
        },
        createdBy: {
          select: {
            id: true,
            username: true,
          },
        },
      },
      orderBy: {
        createdAt: "desc",
      },
    });

    return NextResponse.json(inviteCodes);
  } catch (error) {
    console.error("Error fetching invite codes:", error);
    return NextResponse.json(
      { error: "Failed to fetch invite codes" },
      { status: 500 },
    );
  }
}

export const GET = withMetrics(handleGET);
