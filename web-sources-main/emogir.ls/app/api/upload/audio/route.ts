import { authOptions } from "@/lib/auth";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import { db } from "@/lib/db";
import { getServerSession } from "next-auth";
import { isAccountRestricted } from "@/lib/account-status";
import { withMetrics } from "@/lib/api-wrapper";
import { Session } from "next-auth";

const s3 = new S3Client({
  region: "auto",
  endpoint: process.env.CLOUDFLARE_ENDPOINT as string,
  credentials: {
    accessKeyId: process.env.CLOUDFLARE_ACCESS_KEY_ID as string,
    secretAccessKey: process.env.CLOUDFLARE_SECRET_ACCESS_KEY as string,
  },
});

async function handlePOST(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const isRestricted = await isAccountRestricted(session.user.id);
    if (isRestricted) {
      return NextResponse.json(
        { error: "Account is currently restricted" },
        { status: 403 },
      );
    }

    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const allowedTypes = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg"];
    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json({ error: "Invalid file type" }, { status: 400 });
    }

    const ext = file.type.split("/")[1];

    const fileName = `bios/audio/${session.user.id}/${uuidv4()}.${ext}`;

    const buffer = await file.arrayBuffer();
    await s3.send(
      new PutObjectCommand({
        Bucket: process.env.CLOUDFLARE_BUCKET_NAME,
        Key: fileName,
        Body: Buffer.from(buffer),
        ContentType: file.type,
        ACL: "public-read",
      }),
    );

    const publicUrl = `${process.env.CLOUDFLARE_PUBLIC_URL}/${fileName}`;

    const track = await db.audioTrack.create({
      data: {
        url: publicUrl,
        title: file.name,
        icon: null,
        order: 0,
        appearance: {
          connect: {
            userId: session.user.id,
          },
        },
      },
    });

    return NextResponse.json({
      url: publicUrl,
      title: file.name,
      id: track.id,
    });
  } catch (error) {
    console.error("Error uploading audio:", error);
    return NextResponse.json(
      { error: "Failed to upload audio" },
      { status: 500 },
    );
  }
}

export const POST = withMetrics(handlePOST);
