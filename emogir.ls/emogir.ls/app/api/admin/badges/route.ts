import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { Badge } from "@prisma/client";
import { withMetrics } from "@/lib/api-wrapper";
import type { Session } from "next-auth";

const ADMIN_IDS = ["cm8a3itl40000vdtw948gpfp1", "cm8afkf1n000dpa7h6qhtr50v"];

async function handleGET(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;

    if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
      return new Response("Unauthorized", { status: 401 });
    }

    const { userId, badge } = await req.json();

    const user = await db.user.update({
      where: { id: userId },
      data: {
        badges: {
          push: badge,
        },
      },
    });

    return Response.json(user);
  } catch (error) {
    console.error("Error:", error);
    return new Response("Internal error", { status: 500 });
  }
}

export const GET = withMetrics(handleGET);

export async function DELETE(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
      return new Response("Unauthorized", { status: 401 });
    }

    const { userId, badge } = await req.json();

    const user = await db.user.findUnique({
      where: { id: userId },
      select: { badges: true },
    });

    if (!user) {
      return new Response("User not found", { status: 404 });
    }

    const updatedBadges = (user.badges as string[]).filter(
      (b) => b !== badge,
    ) as Badge[];

    await db.user.update({
      where: { id: userId },
      data: {
        badges: updatedBadges,
      },
    });

    return Response.json({ success: true });
  } catch (error) {
    return new Response("Failed to remove badge", { status: 500 });
  }
}
