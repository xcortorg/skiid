import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const slug = searchParams.get("slug");

  try {
    const guildResponse = await fetch(
      "https://discord.com/api/v9/invites/emogirls?with_counts=true",
    );
    const guildData = await guildResponse.json();

    return NextResponse.json(guildData);
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch Discord data" },
      { status: 500 },
    );
  }
}
