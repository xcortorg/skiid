import { db } from "@/lib/db";
import { NextResponse } from "next/server";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ username: string }> },
): Promise<NextResponse> {
  try {
    const resolvedParams = await params;
    const user = await db.user.findUnique({
      where: { username: resolvedParams.username },
      select: { selectedDomains: true },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    const domains = ["emogir.ls", ...user.selectedDomains];

    return NextResponse.json({ domains });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch domains" },
      { status: 500 },
    );
  }
}
