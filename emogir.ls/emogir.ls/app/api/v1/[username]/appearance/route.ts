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
        select: { id: true },
      });

      if (!user) {
        return Response.json({ error: "User not found" }, { status: 404 });
      }

      const appearance = await db.appearance.findUnique({
        where: { userId: user.id },
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
          audioTracks: {
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
        },
      });

      return Response.json(appearance || {});
    } catch (error) {
      console.error("Error fetching appearance:", error);
      return Response.json({ error: "Internal server error" }, { status: 500 });
    }
  });
}
