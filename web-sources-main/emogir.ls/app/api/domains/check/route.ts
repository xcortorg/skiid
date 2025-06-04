import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { db } from "@/lib/db";
import { authOptions } from "@/lib/auth";
import { Session } from "next-auth";

export async function GET(request: Request) {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;

  if (!session?.user?.id) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const subdomain = searchParams.get("subdomain");
  const domain = searchParams.get("domain");

  if (!subdomain || !domain) {
    return new NextResponse("Missing parameters", { status: 400 });
  }

  try {
    const existing = await db.imageHostDomain.findFirst({
      where: {
        subdomain,
        domain,
      },
    });

    return NextResponse.json({
      available: !existing,
    });
  } catch (error) {
    console.error("Failed to check domain:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
}
