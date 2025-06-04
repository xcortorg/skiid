import { withApiAuth } from "@/lib/api-auth";
import { db } from "@/lib/db";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ username: string }> },
): Promise<Response> {
  const resolvedParams = await params;

  return withApiAuth(req, async (apiToken) => {
    try {
      const user = await db.user.findUnique({
        where: { username: resolvedParams.username },
        select: {
          username: true,
          name: true,
          isPremium: true,
          badges: true,
          iconSettings: {
            select: {
              backgroundColor: true,
              size: true,
              borderRadius: true,
              borderColor: true,
              glowColor: true,
              glowIntensity: true,
            },
          },
          appearance: {
            select: {
              displayName: true,
              bio: true,
              avatar: true,
              banner: true,
              backgroundUrl: true,
              layoutStyle: true,
              containerBackgroundColor: true,
              containerBackdropBlur: true,
              containerBorderColor: true,
              containerBorderWidth: true,
              containerBorderRadius: true,
              containerGlowColor: true,
              containerGlowIntensity: true,
              glassEffect: true,
              avatarBorderColor: true,
              avatarGlowColor: true,
              titleColor: true,
              bioColor: true,
              linksBackgroundColor: true,
              audioTracks: {
                take: 3,
                select: {
                  id: true,
                  url: true,
                  title: true,
                  icon: true,
                  order: true,
                },
                orderBy: {
                  order: "asc",
                },
              },
              audioPlayerEnabled: true,
            },
          },
          links: {
            where: { enabled: true },
            take: 5,
            orderBy: { position: "asc" },
            select: {
              id: true,
              title: true,
              url: true,
              iconUrl: true,
              backgroundColor: true,
              hoverColor: true,
              borderColor: true,
              gap: true,
              primaryTextColor: true,
              secondaryTextColor: true,
              hoverTextColor: true,
              textSize: true,
              iconSize: true,
              iconColor: true,
              iconBgColor: true,
              iconBorderRadius: true,
            },
          },
        },
      });

      if (!user) {
        return Response.json({ error: "User not found" }, { status: 404 });
      }

      return Response.json(user);
    } catch (error) {
      console.error("Error fetching profile:", error);
      return Response.json({ error: "Internal server error" }, { status: 500 });
    }
  });
}
