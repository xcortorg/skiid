import { getServerSession } from "next-auth/next";
import { NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { validateSettingsData } from "@/lib/validations";
import { withMetrics } from "@/lib/api-wrapper";
import { Session } from "next-auth";

async function handleGET(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json(
        { code: "40001", message: "Unauthorized access" },
        { status: 401 },
      );
    }

    const user = await db.user.findUnique({
      where: { id: session.user.id },
      select: {
        name: true,
        username: true,
        pageTitle: true,
        seoDescription: true,
        isPrivate: true,
        selectedDomains: true,
        newLoginVerification: true,
        pinEnabled: true,
        customHostname: true,
        customHostnameId: true,
      },
    });

    return NextResponse.json({
      displayName: user?.name,
      username: user?.username,
      pageTitle: user?.pageTitle,
      seoDescription: user?.seoDescription,
      isPrivate: user?.isPrivate,
      selectedDomains: user?.selectedDomains,
      newLoginVerification: user?.newLoginVerification,
      pinEnabled: user?.pinEnabled,
      customHostname: user?.customHostname,
      customHostnameId: user?.customHostnameId,
    });
  } catch (error) {
    return NextResponse.json(
      { code: "50001", message: "Internal server error" },
      { status: 500 },
    );
  }
}

async function handlePUT(req: Request) {
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

    const body = await req.json();
    const validationErrors = validateSettingsData(body, session.user.username);

    if (typeof body.isPrivate !== "boolean") {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: [
            {
              code: "20010",
              message: "isPrivate must be a boolean value",
              field: "isPrivate",
              value: body.isPrivate,
            },
          ],
        },
        { status: 400 },
      );
    }

    if (body.selectedDomains && body.selectedDomains.length > 3) {
      return NextResponse.json(
        {
          code: "40002",
          message: "Validation failed",
          errors: [
            {
              code: "20009",
              message:
                "You can only select up to 3 domains. Contact support for more domains.",
              field: "selectedDomains",
              value: body.selectedDomains,
            },
          ],
        },
        { status: 400 },
      );
    }

    if (body.username !== session.user.username) {
      if (body.username && body.username.length < 4) {
        return NextResponse.json(
          {
            code: "40002",
            message: "Validation failed",
            errors: [
              {
                code: "20007",
                message:
                  "Username must be at least 4 characters long. Contact support for shorter usernames.",
                field: "username",
                value: body.username,
              },
            ],
          },
          { status: 400 },
        );
      }
    }

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

    if (body.username !== session.user.username) {
      const existingUser = await db.user.findFirst({
        where: {
          username: body.username,
          id: { not: session.user.id },
        },
      });

      if (existingUser) {
        return NextResponse.json(
          {
            code: "40003",
            message: "Validation failed",
            errors: [
              {
                code: "20006",
                message: "Username is already taken",
                field: "username",
                value: body.username,
              },
            ],
          },
          { status: 400 },
        );
      }
    }

    const user = await db.user.update({
      where: { id: session.user.id },
      data: {
        name: body.displayName,
        username: body.username,
        pageTitle: body.pageTitle,
        seoDescription: body.seoDescription,
        isPrivate: body.isPrivate,
        selectedDomains: body.selectedDomains || [],
        newLoginVerification: body.newLoginVerification,
      },
    });

    return NextResponse.json({
      displayName: user.name,
      username: user.username,
      pageTitle: user.pageTitle,
      seoDescription: user.seoDescription,
      isPrivate: user.isPrivate,
      selectedDomains: user.selectedDomains,
      newLoginVerification: user.newLoginVerification,
      customHostname: user.customHostname,
    });
  } catch (error) {
    console.error("PUT Error:", error);
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

export const GET = withMetrics(handleGET);
export const PUT = withMetrics(handlePUT);
