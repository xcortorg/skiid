import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { withMetrics } from "@/lib/api-wrapper";

async function handleGET(
  req: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  try {
    const resolvedParams = await params;

    const user = await db.user.findUnique({
      where: { username: resolvedParams.slug },
      select: { isPrivate: true },
    });

    if (!user) {
      return new NextResponse("Not found", { status: 404 });
    }

    return NextResponse.json({ isPrivate: user.isPrivate });
  } catch (error) {
    console.error("Error:", error);
    return new NextResponse("Internal error", { status: 500 });
  }
}

export const GET = withMetrics(handleGET);
