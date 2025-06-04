import { authOptions } from "@/lib/auth";
import {
  S3Client,
  PutObjectCommand,
  DeleteObjectCommand,
} from "@aws-sdk/client-s3";
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

    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json({ error: "Invalid file type" }, { status: 400 });
    }

    const ext = file.type.split("/")[1];

    const fileName = `bios/avatars/${session.user.id}/${uuidv4()}.${ext}`;

    const existingAppearance = await db.appearance.findUnique({
      where: { userId: session.user.id },
      select: { avatar: true },
    });

    if (existingAppearance?.avatar) {
      const oldKey = existingAppearance.avatar.replace(
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
        console.error("Error deleting old avatar:", deleteError);
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

    await db.appearance.update({
      where: { userId: session.user.id },
      data: { avatar: publicUrl },
    });

    return NextResponse.json({ url: publicUrl });
  } catch (error) {
    console.error("Error uploading avatar:", error);
    return NextResponse.json(
      { error: "Failed to upload avatar" },
      { status: 500 },
    );
  }
}

export const POST = withMetrics(handlePOST);
