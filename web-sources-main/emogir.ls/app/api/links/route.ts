import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { isAccountRestricted } from "@/lib/account-status";
import { Session } from "next-auth";

const ALLOWED_DOMAIN = "r.emogir.ls";

function validateAssetUrl(url: string | null): boolean {
  if (!url) return true;
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.hostname === ALLOWED_DOMAIN;
  } catch {
    return false;
  }
}

export async function GET() {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;

  if (!session?.user) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  const links = await db.link.findMany({
    where: {
      userId: session.user.id,
    },
    take: 5,
    orderBy: {
      position: "asc",
    },
  });

  return NextResponse.json(links);
}

export async function POST(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return new NextResponse("Unauthorized", { status: 401 });
    }

    const isRestricted = await isAccountRestricted(session.user.id);
    if (isRestricted) {
      return NextResponse.json(
        { error: "Account is currently restricted" },
        { status: 403 },
      );
    }

    const body = await req.json();

    if (body.icon && !validateAssetUrl(body.icon)) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: [
            {
              code: "20016",
              message: "Icon URL must be from r.emogir.ls",
              field: "icon",
              value: body.icon,
            },
          ],
        },
        { status: 400 },
      );
    }

    const url =
      body.url && !body.url.startsWith("http")
        ? `https://${body.url}`
        : body.url;

    const existingLinksCount = await db.link.count({
      where: { userId: session.user.id },
    });

    if (existingLinksCount >= 20) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: [
            {
              code: "20017",
              message: "Maximum of 20 links allowed",
              field: "links",
              value: existingLinksCount + 1,
            },
          ],
        },
        { status: 400 },
      );
    }

    const link = await db.link.create({
      data: {
        ...body,
        url,
        userId: session.user.id,
      },
    });

    return NextResponse.json(link);
  } catch (error) {
    console.error("Error creating link:", error);
    return NextResponse.json(
      { error: "Failed to create link" },
      { status: 500 },
    );
  }
}

export async function PUT(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return new NextResponse("Unauthorized", { status: 401 });
    }

    const isRestricted = await isAccountRestricted(session.user.id);
    if (isRestricted) {
      return NextResponse.json(
        { error: "Account is currently restricted" },
        { status: 403 },
      );
    }

    const body = await req.json();

    if (!body.positions) {
      const existingLinksCount = await db.link.count({
        where: {
          userId: session.user.id,
          NOT: { id: body.id },
        },
      });

      if (existingLinksCount >= 20) {
        return NextResponse.json(
          {
            code: "40002",
            message: "Validation failed",
            errors: [
              {
                code: "20017",
                message: "Maximum of 20 links allowed",
                field: "links",
                value: existingLinksCount + 1,
              },
            ],
          },
          { status: 400 },
        );
      }

      if (body.icon && !validateAssetUrl(body.icon)) {
        return NextResponse.json(
          {
            code: "40002",
            message: "Validation failed",
            errors: [
              {
                code: "20016",
                message: "Icon URL must be from r.emogir.ls",
                field: "icon",
                value: body.icon,
              },
            ],
          },
          { status: 400 },
        );
      }

      const url =
        body.url && !body.url.startsWith("http")
          ? `https://${body.url}`
          : body.url;
      const link = await db.link.update({
        where: {
          id: body.id,
          userId: session.user.id,
        },
        data: {
          ...body,
          url,
        },
      });
      return NextResponse.json(link);
    }

    // handle multiple positions update
    const updates = body.positions.map((p: { id: string; position: number }) =>
      db.link.update({
        where: { id: p.id, userId: session.user.id },
        data: { position: p.position },
      }),
    );
    await db.$transaction(updates);
    return NextResponse.json({ message: "Positions updated" });
  } catch (error) {
    console.error("Error updating link:", error);
    return NextResponse.json(
      { error: "Failed to update link" },
      { status: 500 },
    );
  }
}

export async function DELETE(req: Request) {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;

  if (!session?.user) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  const isRestricted = await isAccountRestricted(session.user.id);
  if (isRestricted) {
    return NextResponse.json(
      { error: "Account is currently restricted" },
      { status: 403 },
    );
  }

  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");

  if (!id) {
    return new NextResponse("Missing link ID", { status: 400 });
  }

  await db.link.delete({
    where: {
      id,
      userId: session.user.id,
    },
  });

  return NextResponse.json({ success: true });
}
