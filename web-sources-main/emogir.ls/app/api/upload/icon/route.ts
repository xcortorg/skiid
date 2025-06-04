import { authOptions } from "@/lib/auth";
import {
  S3Client,
  PutObjectCommand,
  DeleteObjectCommand,
} from "@aws-sdk/client-s3";
import { NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import { getServerSession } from "next-auth";
import { db } from "@/lib/db";
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
    const trackId = formData.get("trackId") as string;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const allowedTypes = [
      "image/jpeg",
      "image/png",
      "image/webp",
      "image/svg+xml",
    ];
    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json({ error: "Invalid file type" }, { status: 400 });
    }

    const ext = file.type.split("/")[1];

    const fileName = `bios/icons/${session.user.id}/${uuidv4()}.${ext}`;

    if (trackId) {
      const existingTrack = await db.audioTrack.findUnique({
        where: { id: trackId },
        select: { icon: true },
      });

      if (existingTrack?.icon) {
        const oldKey = existingTrack.icon.replace(
          `${process.env.CLOUDFLARE_PUBLIC_URL}/`,
          "",
        );
        try {
          await s3.send(
            new DeleteObjectCommand({
              Bucket: process.env.CLOUDFLARE_BUCKET_NAME,
              Key: oldKey,
            }),
          );
        } catch (deleteError) {
          console.error("Error deleting old icon:", deleteError);
        }
      }
    }

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

    if (trackId) {
      await db.audioTrack.update({
        where: { id: trackId },
        data: { icon: publicUrl },
      });
    }

    return NextResponse.json({ url: publicUrl });
  } catch (error) {
    console.error("Error uploading icon:", error);
    return NextResponse.json(
      { error: "Failed to upload icon" },
      { status: 500 },
    );
  }
}

export const POST = withMetrics(handlePOST);
