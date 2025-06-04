import { NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const hostname = url.searchParams.get("hostname");

    if (!hostname) {
      return NextResponse.json(
        { error: "Hostname parameter is required" },
        { status: 400 },
      );
    }

    const user = await db.user.findFirst({
      where: {
        customHostname: hostname,
      },
      select: {
        username: true,
        id: true,
        name: true,
        image: true,
        isPrivate: true,
      },
    });

    if (!user) {
      return NextResponse.json(
        { error: "No user found with this hostname" },
        { status: 404 },
      );
    }

    return NextResponse.json({
      username: user.username,
      displayName: user.name,
      id: user.id,
      image: user.image,
      isPrivate: user.isPrivate,
    });
  } catch (error) {
    console.error("Error looking up hostname:", error);
    return NextResponse.json(
      { error: "Failed to lookup hostname" },
      { status: 500 },
    );
  }
}
