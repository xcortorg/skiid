import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import crypto from "crypto";
import { Session } from "next-auth";

function generateSignature(params: Record<string, string>, secret: string) {
  const sortedKeys = Object.keys(params).sort();
  const signatureBase = sortedKeys
    .map((key) => `${key}${params[key]}`)
    .join("");

  return crypto
    .createHash("md5")
    .update(signatureBase + secret)
    .digest("hex");
}

export async function GET(req: Request) {
  const baseUrl =
    process.env.NODE_ENV === "production"
      ? "https://emogir.ls"
      : "http://localhost:3000";

  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;
  if (!session?.user?.id) {
    return NextResponse.redirect(
      `https://emogir.ls/dashboard/settings?error=unauthorized`,
    );
  }

  const { searchParams } = new URL(req.url);
  const token = searchParams.get("token");

  if (!token) {
    return NextResponse.redirect(
      `https://emogir.ls/dashboard/settings?error=no_token`,
    );
  }

  try {
    const params = {
      method: "auth.getSession",
      api_key: process.env.LASTFM_API_KEY!,
      token: token,
    };

    const apiSig = generateSignature(params, process.env.LASTFM_SECRET!);

    const response = await fetch(
      `http://ws.audioscrobbler.com/2.0/?${new URLSearchParams({
        ...params,
        api_sig: apiSig,
        format: "json",
      })}`,
    );

    console.log("Last.fm response status:", response.status);
    const data = await response.json();
    console.log("Last.fm response:", data);

    if (!data.session?.name) {
      throw new Error("No username in Last.fm response");
    }

    await db.account.upsert({
      where: {
        provider_providerAccountId: {
          provider: "lastfm",
          providerAccountId: data.session.name,
        },
      },
      update: {
        access_token: data.session.key,
        userId: session.user.id,
      },
      create: {
        userId: session.user.id,
        type: "oauth",
        provider: "lastfm",
        providerAccountId: data.session.name,
        access_token: data.session.key,
      },
    });

    return NextResponse.redirect(
      `https://emogir.ls/dashboard/settings?success=lastfm_connected`,
    );
  } catch (error) {
    console.error("Last.fm connection error:", error);
    return NextResponse.redirect(
      `https://emogir.ls/dashboard/settings?error=connection_failed`,
    );
  }
}
