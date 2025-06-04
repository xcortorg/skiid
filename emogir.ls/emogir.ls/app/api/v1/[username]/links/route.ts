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

      const { searchParams } = new URL(req.url);
      const limit = parseInt(searchParams.get("limit") || "50");
      const offset = parseInt(searchParams.get("offset") || "0");

      const links = await db.link.findMany({
        where: { userId: user.id },
        orderBy: { position: "asc" },
        take: Math.min(limit, 100),
        skip: offset,
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

      return Response.json(links);
    } catch (error) {
      console.error("Error fetching links:", error);
      return Response.json({ error: "Internal server error" }, { status: 500 });
    }
  });
}
