import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { db } from "@/lib/db";
import { authOptions } from "@/lib/auth";
import { Session } from "next-auth";

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;

  if (!session?.user?.id) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  try {
    const resolvedParams = await params;
    const upload = await db.upload.findUnique({
      where: { id: resolvedParams.id },
    });

    if (!upload || upload.userId !== session.user.id) {
      return new NextResponse("Not found", { status: 404 });
    }

    await db.upload.delete({
      where: { id: resolvedParams.id },
    });

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    console.error("Failed to delete upload:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
}
