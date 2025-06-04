import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { sendDiscordWebhook } from "@/lib/discord";

const DISCORD_WEBHOOK_URL =
  "https://discord.com/api/webhooks/1351675743645732957/6QYyPFjHQD0Pn9EHINPmaRqSUiIl4mexLidfDgZ0hyNVRb-48frn1NQYpv7THwrOvcS3";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { type, targetId, reason, details, email } = body;

    if (!type || !targetId || !reason || !details) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 },
      );
    }

    const report = await db.report.create({
      data: {
        type,
        targetId,
        reason,
        details,
        email: email || null,
        status: "pending",
      },
    });

    await sendDiscordWebhook(DISCORD_WEBHOOK_URL, "🚨 New Report Submitted", [
      {
        title: `${type.charAt(0).toUpperCase() + type.slice(1)} Report`,
        color: 0xff0000,
        fields: [
          {
            name: "Type",
            value: type,
            inline: true,
          },
          {
            name: "Target",
            value: targetId,
            inline: true,
          },
          {
            name: "Reason",
            value: reason,
            inline: true,
          },
          {
            name: "Details",
            value: details || "No details provided",
          },
          {
            name: "Contact",
            value: email || "No email provided",
            inline: true,
          },
          {
            name: "Report ID",
            value: report.id,
            inline: true,
          },
        ],
        timestamp: new Date().toISOString(),
      },
    ]);

    return NextResponse.json({
      success: true,
      message: "Report submitted successfully",
      reportId: report.id,
    });
  } catch (error) {
    console.error("Error creating report:", error);
    return NextResponse.json(
      { error: "Failed to submit report" },
      { status: 500 },
    );
  }
}
