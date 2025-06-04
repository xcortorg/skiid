import { connectDiscord } from "@/lib/discord";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { Session } from "next-auth";

export async function GET(req: Request) {
  const baseUrl =
    process.env.NODE_ENV === "production"
      ? "https://emogir.ls"
      : "http://localhost:3000";

  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;
  if (!session?.user?.email) {
    return NextResponse.redirect(`https://emogir.ls/login`);
  }

  const { searchParams } = new URL(req.url);
  const code = searchParams.get("code");

  if (!code) {
    return NextResponse.redirect(
      `https://emogir.ls/dashboard/settings?error=no_code`,
    );
  }

  try {
    const { tokens, user } = await connectDiscord(code);

    const existingAccount = await db.account.findFirst({
      where: {
        provider: "discord",
        providerAccountId: user.id,
      },
    });

    if (existingAccount) {
      if (existingAccount.userId === session.user.id) {
        await db.account.update({
          where: {
            id: existingAccount.id
          },
          data: {
            access_token: tokens.access_token,
            token_type: tokens.token_type,
            expires_at: Math.floor(Date.now() / 1000 + tokens.expires_in),
            refresh_token: tokens.refresh_token,
            scope: tokens.scope,
            providerAccountId: user.id,
          }
        });
        
        return NextResponse.redirect(
          `https://emogir.ls/dashboard/settings?success=discord_updated`,
        );
      } else {
        return NextResponse.redirect(
          `https://emogir.ls/dashboard/settings?error=account_in_use`,
        );
      }
    }

    await db.account.create({
      data: {
        userId: session.user.id,
        type: "oauth",
        provider: "discord",
        providerAccountId: user.id,
        access_token: tokens.access_token,
        token_type: tokens.token_type,
        expires_at: Math.floor(Date.now() / 1000 + tokens.expires_in),
        refresh_token: tokens.refresh_token,
        scope: tokens.scope,
      },
    });

    return NextResponse.redirect(
      `https://emogir.ls/dashboard/settings?success=discord_connected`,
    );
  } catch (error) {
    console.error("Error connecting Discord:", error);
    return NextResponse.redirect(
      `https://emogir.ls/dashboard/settings?error=connection_failed`,
    );
  }
}
