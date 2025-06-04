import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { Session } from "next-auth";

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ tokenId: string }> },
) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const resolvedParams = await params;
    await db.apiToken.update({
      where: {
        id: resolvedParams.tokenId,
        userId: session.user.id,
      },
      data: {
        isActive: false,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Token revocation error:", error);
    return NextResponse.json(
      { error: "Failed to revoke token" },
      { status: 500 },
    );
  }
}
