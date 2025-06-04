import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import {
  createCustomHostname,
  findHostnameIdentifier,
  getCustomHostname,
} from "@/lib/cloudflare";
import { Session } from "next-auth";

export async function POST(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;

    if (!session?.user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const user = await db.user.findUnique({
      where: { email: session.user.email },
      include: { features: true },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    const isPremiumActive =
      user.isPremium &&
      (!user.premiumUntil || new Date(user.premiumUntil) > new Date());

    if (!isPremiumActive || !user.features?.customDomain) {
      return NextResponse.json(
        { error: "Premium subscription required for custom domains" },
        { status: 403 },
      );
    }

    const { hostname } = await req.json();

    if (!hostname) {
      return NextResponse.json(
        { error: "Hostname is required" },
        { status: 400 },
      );
    }

    const userHostnameCount = await db.user.count({
      where: {
        id: user.id,
        customHostname: {
          not: null,
        },
        NOT: {
          customHostname: hostname,
        },
      },
    });

    if (userHostnameCount >= 2) {
      return NextResponse.json(
        { error: "Maximum of 2 custom hostnames allowed per user" },
        { status: 400 },
      );
    }

    const existingUser = await db.user.findFirst({
      where: {
        customHostname: hostname,
        id: { not: user.id },
      },
    });

    if (existingUser) {
      return NextResponse.json(
        { error: "This hostname is already in use" },
        { status: 400 },
      );
    }

    const existingIdentifier = await findHostnameIdentifier(hostname);

    if (!existingIdentifier) {
      const customHostname = await createCustomHostname(hostname);

      await db.user.update({
        where: { id: user.id },
        data: {
          customHostname: hostname,
          customHostnameId: customHostname.id,
        },
      });

      const verificationInstructions: {
        verified: boolean;
        message: string;
        step: number;
        hostname: string;
        id: string;
        records: Array<{ type: string; name: string; value: string }>;
      } = {
        verified: false,
        message:
          "Domain verification initiated. Please add the following DNS records to your domain settings:",
        step: 1,
        hostname: customHostname.hostname,
        id: customHostname.id,
        records: [],
      };

      if (customHostname.ownership_verification) {
        verificationInstructions.records.push({
          type: customHostname.ownership_verification.type.toUpperCase(),
          name: customHostname.ownership_verification.name,
          value: customHostname.ownership_verification.value,
        });
      }

      if (customHostname.ssl?.validation_records) {
        customHostname.ssl.validation_records.forEach((record) => {
          if (record.txt_name && record.txt_value) {
            verificationInstructions.records.push({
              type: "TXT",
              name: record.txt_name,
              value: record.txt_value,
            });
          }
        });
      }

      verificationInstructions.records.push({
        type: "CNAME",
        name: "@",
        value: "cname.emogir.ls",
      });

      return NextResponse.json(verificationInstructions);
    } else {
      const customHostname = await getCustomHostname(existingIdentifier);

      await db.user.update({
        where: { id: user.id },
        data: {
          customHostname: hostname,
          customHostnameId: existingIdentifier,
        },
      });

      if (
        customHostname.ssl?.status === "pending_validation" &&
        customHostname.ssl?.validation_records
      ) {
        const verificationInstructions: {
          verified: boolean;
          message: string;
          step: number;
          hostname: string;
          id: string;
          records: Array<{ type: string; name: string; value: string }>;
        } = {
          verified: false,
          message:
            "Domain verified, but SSL certificate is still pending. Please add the following DNS records:",
          step: 2,
          hostname: customHostname.hostname,
          id: customHostname.id,
          records: [],
        };

        customHostname.ssl.validation_records.forEach((record) => {
          if (record.txt_name && record.txt_value) {
            verificationInstructions.records.push({
              type: "TXT",
              name: record.txt_name,
              value: record.txt_value,
            });
          }
        });

        return NextResponse.json(verificationInstructions);
      }

      return NextResponse.json({
        verified: customHostname.status === "active",
        ssl_status: customHostname.ssl?.status || "pending",
        message:
          customHostname.status === "active" &&
          customHostname.ssl?.status === "active"
            ? "Domain is verified and SSL certificate is active"
            : "Domain is verified but SSL certificate is still processing",
        hostname,
        id: existingIdentifier,
      });
    }
  } catch (error) {
    console.error("Error verifying domain:", error);
    return NextResponse.json(
      { error: "Failed to verify domain" },
      { status: 500 },
    );
  }
}
