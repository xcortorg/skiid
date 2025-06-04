import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { validateIconSettings } from "@/lib/validations";
import { Session } from "next-auth";

export async function PUT(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json(
        {
          code: "40001",
          message: "Unauthorized access",
        },
        { status: 401 },
      );
    }

    const settings = await req.json();
    const validationErrors = validateIconSettings(settings);

    if (validationErrors.length > 0) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: validationErrors,
        },
        { status: 400 },
      );
    }

    const updated = await db.iconSettings.upsert({
      where: { userId: session.user.id },
      create: {
        userId: session.user.id,
        ...settings,
      },
      update: settings,
    });

    return NextResponse.json(updated);
  } catch (error) {
    console.error("Error updating icon settings:", error);
    return NextResponse.json(
      {
        code: "50001",
        message: "Internal server error",
        errors: [
          {
            code: "50001",
            message: "An unexpected error occurred",
            field: "server",
          },
        ],
      },
      { status: 500 },
    );
  }
}

export async function GET(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const settings = await db.iconSettings.findFirst({
      where: { userId: session.user.id },
    });

    // Mr B.... Next time please make sure to return default values if there are none.
    // no bitch ass nigga
    return NextResponse.json(
      settings || {
        userId: session.user.id,
        backgroundColor: "",
        iconColor: "",
        borderColor: "",
        borderWidth: 0,
        borderRadius: 0,
        padding: 0,
        gap: 0,
      },
    );
  } catch (error) {
    console.error("Error fetching icon settings:", error);
    return NextResponse.json(
      { error: "Failed to fetch icon settings" },
      { status: 500 },
    );
  }
}
