import { NextRequest, NextResponse } from "next/server";
import { PutObjectCommand } from "@aws-sdk/client-s3";
import { r2Client } from "@/lib/r2";
import { supabase } from "@/lib/supabase";
import { config as appConfig } from "@/lib/config";

export async function POST(request: NextRequest) {
  const apiKey = request.headers.get("Authorization")?.replace("Bearer ", "");
  if (!apiKey) {
    return NextResponse.json({ error: "Missing API key" }, { status: 401 });
  }

  const { data: user, error } = await supabase
    .from("image_users")
    .select("id, subdomain, active")
    .eq("api_key", apiKey)
    .single();

  if (error || !user) {
    return NextResponse.json({ error: "Invalid API key" }, { status: 401 });
  }

  if (!user.active) {
    return NextResponse.json(
      { error: "User account is inactive" },
      { status: 403 }
    );
  }

  try {
    const formData = await request.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const { data: usage, error: usageError } = await supabase
      .from("uploads")
      .select("size")
      .eq("user_id", user.id);

    if (usageError) {
      return NextResponse.json(
        { error: "Error checking storage usage" },
        { status: 500 }
      );
    }

    const currentUsage = usage.reduce(
      (total, upload) => total + upload.size,
      0
    );
    const maxStorage = 10 * 1024 * 1024 * 1024;

    if (currentUsage + file.size > maxStorage) {
      return NextResponse.json(
        { error: "Storage limit exceeded" },
        { status: 400 }
      );
    }

    function generateFileName(): string {
      const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
      let result = '';
      for (let i = 0; i < 5; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
      }

      for (let i = 0; i < 2; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      return result;
    }

    const buffer = await file.arrayBuffer();
    const fileExt = file.name.split(".").pop();
    const fileName = `${generateFileName()}.${fileExt}`;

    await r2Client.send(
      new PutObjectCommand({
        Bucket: appConfig.bucketName,
        Key: fileName,
        Body: Buffer.from(buffer),
        ContentType: file.type,
      })
    );

    await supabase.from("uploads").insert({
      user_id: user.id,
      filename: fileName,
      original_name: file.name,
      size: file.size,
      mime_type: file.type,
    });

    return NextResponse.json({
      url: `https://${user.subdomain}/${fileName}`,
    });
  } catch (error) {
    console.error("Upload error:", error);
    return NextResponse.json({ error: "Upload failed" }, { status: 500 });
  }
}

export const config = {
  api: {
    bodyParser: false,
  },
};
