import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { withMetrics } from "@/lib/api-wrapper";

async function handleGET() {
  try {
    const decorationsDir = path.join(process.cwd(), "public", "decorations");

    if (!fs.existsSync(decorationsDir)) {
      console.error("Decorations directory not found:", decorationsDir);
      return NextResponse.json(
        { decorations: [], error: "Directory not found" },
        { status: 404 },
      );
    }

    const files = fs.readdirSync(decorationsDir);

    const decorations = files.filter(
      (file) =>
        file.toLowerCase().endsWith(".png") ||
        file.toLowerCase().endsWith(".jpg") ||
        file.toLowerCase().endsWith(".jpeg") ||
        file.toLowerCase().endsWith(".gif"),
    );

    console.log(`Found ${decorations.length} decoration files`);

    return NextResponse.json({ decorations });
  } catch (error) {
    console.error("Error fetching decorations:", error);
    return NextResponse.json(
      { decorations: [], error: "Failed to fetch decorations" },
      { status: 500 },
    );
  }
}

export const GET = withMetrics(handleGET);
