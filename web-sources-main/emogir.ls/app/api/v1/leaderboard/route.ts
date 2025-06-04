import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { withApiAuth } from "@/lib/api-auth";

export async function GET(req: Request) {
  return withApiAuth(req, async (apiToken) => {
    try {
      const url = new URL(req.url);
      const limit = parseInt(url.searchParams.get("limit") || "20");
      const page = parseInt(url.searchParams.get("page") || "1");
      const skip = (page - 1) * limit;

      const viewCounts = await db.pageView.groupBy({
        by: ["slug"],
        _count: {
          _all: true,
        },
        orderBy: {
          _count: {
            slug: "desc",
          },
        },
        take: limit,
        skip: skip,
      });

      const topProfiles = await db.user.findMany({
        where: {
          username: {
            in: viewCounts.map((vc) => vc.slug),
          },
        },
        select: {
          username: true,
          name: true,
          appearance: {
            select: {
              avatar: true,
              banner: true,
              backgroundUrl: true,
              displayName: true,
              bio: true,
            },
          },
          badges: true,
          isPremium: true,
        },
      });

      const formattedProfiles = viewCounts
        .map((vc) => {
          const profile = topProfiles.find((p) => p.username === vc.slug);
          if (!profile) return null;
          return {
            username: profile.username,
            displayName: profile.name || profile.username,
            avatar: profile.appearance?.avatar || null,
            banner: profile.appearance?.banner || null,
            backgroundUrl: profile.appearance?.backgroundUrl || null,
            bio: profile.appearance?.bio || null,
            views: vc._count._all,
            badges: profile.badges,
            isPremium: profile.isPremium,
          };
        })
        .filter(Boolean);

      const totalProfiles = await db.user.count();

      return NextResponse.json({
        profiles: formattedProfiles,
        pagination: {
          total: totalProfiles,
          page,
          limit,
          pages: Math.ceil(totalProfiles / limit),
        },
      });
    } catch (error) {
      console.error("Leaderboard Error:", error);
      return NextResponse.json(
        { error: "Failed to fetch leaderboard" },
        { status: 500 },
      );
    }
  });
}
