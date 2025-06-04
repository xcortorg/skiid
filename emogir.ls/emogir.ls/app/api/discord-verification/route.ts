import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

const DISCORD_AUTH_TOKEN = process.env.DISCORD_AUTH_TOKEN;

export async function POST(request: Request) {
  try {
    const authHeader = request.headers.get("authorization");
    if (
      !authHeader?.startsWith("Bearer ") ||
      authHeader.split(" ")[1] !== DISCORD_AUTH_TOKEN
    ) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { user_id, content, domain = "emogir.ls" } = body;

    if (!user_id || !content) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 },
      );
    }

    const { data: existingData } = await supabase
      .from("discord_verifications")
      .select("content")
      .eq("domain", domain)
      .order("created_at", { ascending: false });

    await supabase
      .from("discord_verifications")
      .insert([{ user_id, content, domain }]);

    const allContent = [
      content,
      ...(existingData?.map((d) => d.content) || []),
    ].join("\n");

    if (domain === "emogir.ls") {
      await supabase
        .from("discord_verification_file")
        .upsert({ id: 1, content: allContent }, { onConflict: "id" });
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}

export async function GET() {
  try {
    const { data } = await supabase
      .from("discord_verification_file")
      .select("content")
      .eq("id", 1)
      .single();

    return new NextResponse(data?.content || "", {
      status: 200,
      headers: {
        "Content-Type": "text/plain",
      },
    });
  } catch (error) {
    console.error("Error:", error);
    return new NextResponse("", { status: 500 });
  }
}
