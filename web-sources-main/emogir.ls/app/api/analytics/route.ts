import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { Session } from "next-auth";
import { db } from "@/lib/db";

const PLAUSIBLE_API_KEY = process.env.PLAUSIBLE_API_KEY;
const PLAUSIBLE_BASE_URL = "https://plausible.emogir.ls/api/v1/stats";

export async function GET(req: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any
    )) as Session | null;
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const user = await db.user.findUnique({
      where: { id: session.user.id },
      select: { name: true },
    });

    if (!user?.name) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    const { searchParams } = new URL(req.url);
    const period = searchParams.get("period") || "30d";
    const userSlug = user.name.toLowerCase();
    const pageFilter = `event:page==/@${userSlug}`;

    async function fetchPlausibleStats(endpoint: string) {
      const url = `${PLAUSIBLE_BASE_URL}/${endpoint}`;
      console.log("Fetching:", decodeURIComponent(url));

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${PLAUSIBLE_API_KEY}`,
        },
      });
      return response.json();
    }

    const [aggregate, browsers, devices, locations, sources, timeseries] =
      await Promise.all([
        fetchPlausibleStats(
          `aggregate?site_id=emogir.ls&period=${period}&metrics=visitors,pageviews,bounce_rate,visit_duration&filters=${encodeURIComponent(
            pageFilter
          )}`
        ),
        fetchPlausibleStats(
          `breakdown?site_id=emogir.ls&period=${period}&property=visit:browser&metrics=visitors&filters=${encodeURIComponent(
            pageFilter
          )}`
        ),
        fetchPlausibleStats(
          `breakdown?site_id=emogir.ls&period=${period}&property=visit:device&metrics=visitors&filters=${encodeURIComponent(
            pageFilter
          )}`
        ),
        fetchPlausibleStats(
          `breakdown?site_id=emogir.ls&period=${period}&property=visit:country&metrics=visitors&filters=${encodeURIComponent(
            pageFilter
          )}`
        ),
        fetchPlausibleStats(
          `breakdown?site_id=emogir.ls&period=${period}&property=visit:source&metrics=visitors&filters=${encodeURIComponent(
            pageFilter
          )}`
        ),
        fetchPlausibleStats(
          `timeseries?site_id=emogir.ls&period=day&filters=${encodeURIComponent(
            pageFilter
          )}`
        ),
      ]);

    return NextResponse.json({
      aggregate,
      browsers,
      devices,
      locations,
      sources,
      timeseries,
    });
  } catch (error) {
    console.error("Error fetching analytics:", error);
    return NextResponse.json(
      { error: "Failed to fetch analytics data" },
      { status: 500 }
    );
  }
}
