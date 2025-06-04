import { withApiAuth } from "@/lib/api-auth";
import { db } from "@/lib/db";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ username: string; linkId: string }> },
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

      const link = await db.link.findFirst({
        where: {
          id: resolvedParams.linkId,
          userId: user.id,
        },
        select: {
          id: true,
          title: true,
          url: true,
          iconUrl: true,
          enabled: true,
          position: true,
          clicks: true,
        },
      });

      if (!link) {
        return Response.json({ error: "Link not found" }, { status: 404 });
      }

      return Response.json(link);
    } catch (error) {
      console.error("Error fetching link:", error);
      return Response.json({ error: "Internal server error" }, { status: 500 });
    }
  });
}
