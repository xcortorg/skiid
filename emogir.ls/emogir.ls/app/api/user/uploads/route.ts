import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { db } from "@/lib/db";
import { authOptions } from "@/lib/auth";
import { Session } from "next-auth";

export async function GET() {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;

  if (!session?.user?.id) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  try {
    const uploads = await db.upload.findMany({
      where: {
        userId: session.user.id,
      },
      orderBy: {
        createdAt: "desc",
      },
    });

    return NextResponse.json(uploads);
  } catch (error) {
    console.error("Failed to fetch uploads:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
}
