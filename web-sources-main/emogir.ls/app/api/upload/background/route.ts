import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import {
  S3Client,
  PutObjectCommand,
  DeleteObjectCommand,
} from "@aws-sdk/client-s3";
import { NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
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

const MAX_FILE_SIZE = {
  image: 8 * 1024 * 1024,
  video: 45 * 1024 * 1024,
};

async function handlePOST(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const isRestricted = await isAccountRestricted(session.user.id);
    if (isRestricted) {
      return NextResponse.json(
        { error: "Account is currently restricted" },
        { status: 403 }
      );
    }

    const formData = await req.formData();
    const file = formData.get("file") as File;
    const type = formData.get("type") as "background" | "banner";

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const allowedImageTypes = [
      "image/jpeg",
      "image/png",
      "image/webp",
      "image/gif",
    ];
    const allowedVideoTypes = ["video/mp4"];
    const isImage = allowedImageTypes.includes(file.type);
    const isVideo = allowedVideoTypes.includes(file.type);

    if (!isImage && !isVideo) {
      return NextResponse.json(
        {
          error: "Invalid file type. Allowed types: JPEG, PNG, WebP, GIF, MP4",
        },
        { status: 400 }
      );
    }

    const maxSize = isVideo ? MAX_FILE_SIZE.video : MAX_FILE_SIZE.image;
    if (file.size > maxSize) {
      return NextResponse.json(
        {
          error: `File too large. Maximum size: ${maxSize / (1024 * 1024)}MB`,
        },
        { status: 400 }
      );
    }

    const existingAppearance = await db.appearance.findUnique({
      where: { userId: session.user.id },
      select: { backgroundUrl: true, banner: true },
    });

    const oldUrl =
      type === "banner"
        ? existingAppearance?.banner
        : existingAppearance?.backgroundUrl;
    if (oldUrl) {
      const oldKey = oldUrl.replace(
        `${process.env.CLOUDFLARE_PUBLIC_URL}/`,
        ""
      );
      try {
        await s3.send(
          new DeleteObjectCommand({
            Bucket: process.env.CLOUDFLARE_BUCKET_NAME,
            Key: oldKey,
          })
        );
      } catch (deleteError) {
        console.error("Error deleting old file:", deleteError);
      }
    }

    const ext = file.type.split("/")[1];
    const fileName = `bios/${type}s/${session.user.id}/${uuidv4()}.${ext}`;

    const buffer = await file.arrayBuffer();
    await s3.send(
      new PutObjectCommand({
        Bucket: process.env.CLOUDFLARE_BUCKET_NAME,
        Key: fileName,
        Body: Buffer.from(buffer),
        ContentType: file.type,
        ACL: "public-read",
      })
    );

    const publicUrl = `${process.env.CLOUDFLARE_PUBLIC_URL}/${fileName}`;

    const updateField = type === "banner" ? "banner" : "backgroundUrl";
    await db.appearance.update({
      where: { userId: session.user.id },
      data: { [updateField]: publicUrl },
    });

    return NextResponse.json({ url: publicUrl });
  } catch (error) {
    console.error("Error uploading file:", error);
    return NextResponse.json(
      { error: "Failed to upload file" },
      { status: 500 }
    );
  }
}

export const POST = withMetrics(handlePOST);
