import { NextResponse } from "next/server";

const USERS_API_URL = "https://users.emogir.ls/users";
const API_KEY = process.env.DISCORD_USERS_API_KEY;

if (!API_KEY) {
  throw new Error(
    "DISCORD_USERS_API_KEY is not defined in environment variables"
  );
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const resolvedParams = await params;
    
    const response = await fetch(`${USERS_API_URL}/${resolvedParams.id}`, {
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        Accept: "application/json",
      },
      next: { revalidate: 60 },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch user data: ${response.statusText}`);
    }

    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching Discord user data:", error);
    return NextResponse.json(
      { error: "Failed to fetch Discord user data" },
      { status: 500 }
    );
  }
}
