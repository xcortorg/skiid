import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { hash, compare } from "bcrypt";
import { Session } from "next-auth";

export async function POST(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json(
        { code: "40001", message: "Unauthorized" },
        { status: 401 },
      );
    }

    const { pin, enabled } = await req.json();

    console.log("Updating PIN settings:", { enabled, hasPin: !!pin });

    if (enabled && (!pin || pin.length !== 6)) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: [
            {
              code: "20011",
              message: "PIN must be exactly 6 digits",
              field: "pin",
            },
          ],
        },
        { status: 400 },
      );
    }

    const pinHash = enabled ? await hash(pin, 10) : null;

    const updatedUser = await db.user.update({
      where: { id: session.user.id },
      data: {
        pinEnabled: enabled,
        pinHash: pinHash,
      },
      select: {
        pinEnabled: true,
      },
    });

    console.log("Updated user PIN settings:", updatedUser);

    return NextResponse.json({
      success: true,
      pinEnabled: updatedUser.pinEnabled,
    });
  } catch (error) {
    console.error("PIN Error:", error);
    return NextResponse.json(
      { code: "50001", message: "Internal server error" },
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
      return NextResponse.json(
        { code: "40001", message: "Unauthorized" },
        { status: 401 },
      );
    }

    const { pin } = await req.json();

    const user = await db.user.findUnique({
      where: { id: session.user.id },
      select: { pinHash: true },
    });

    if (!user?.pinHash) {
      return NextResponse.json(
        { code: "40003", message: "PIN not set" },
        { status: 400 },
      );
    }

    const isValid = await compare(pin, user.pinHash);
    return NextResponse.json({ isValid });
  } catch (error) {
    return NextResponse.json(
      { code: "50001", message: "Internal server error" },
      { status: 500 },
    );
  }
}
