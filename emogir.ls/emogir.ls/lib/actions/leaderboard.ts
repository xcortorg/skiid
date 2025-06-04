"use server";

import { db } from "@/lib/db";

export async function fetchTopProfiles() {
  try {
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
      take: 25,
    });

    const topProfiles = await db.user.findMany({
      where: {
        username: {
          in: viewCounts.map((vc) => vc.slug),
        },
      },
      select: {
        username: true,
        appearance: {
          select: {
            avatar: true,
            displayName: true,
          },
        },
      },
    });

    return viewCounts
      .map((vc) => {
        const profile = topProfiles.find((p) => p.username === vc.slug);
        if (!profile) return null;
        return {
          username: profile.username,
          displayName: profile.appearance?.displayName || profile.username,
          avatar: profile.appearance?.avatar || null,
          views: vc._count._all,
        };
      })
      .filter(Boolean);
  } catch (error) {
    console.error("Error fetching top profiles:", error);
    return [];
  }
}
