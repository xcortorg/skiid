import { NextResponse } from "next/server";
import { db } from "@/lib/db";

const LASTFM_API_KEY = process.env.LASTFM_API_KEY;
const LASTFM_BASE_URL = "https://ws.audioscrobbler.com/2.0/";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const slug = searchParams.get("slug");

    if (!slug) {
      return NextResponse.json(
        { error: "Slug parameter is required" },
        { status: 400 }
      );
    }

    const user = await db.user.findUnique({
      where: { username: slug },
      select: { id: true },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    const account = await db.account.findFirst({
      where: {
        userId: user.id,
        provider: "lastfm",
      },
    });

    if (!account) {
      return NextResponse.json(
        { error: "Last.fm account not connected" },
        { status: 404 }
      );
    }

    const lastfmUsername = account.providerAccountId;

    const recentTracksUrl = new URL(LASTFM_BASE_URL);
    recentTracksUrl.searchParams.append("method", "user.getrecenttracks");
    recentTracksUrl.searchParams.append("user", lastfmUsername);
    recentTracksUrl.searchParams.append("api_key", LASTFM_API_KEY || "");
    recentTracksUrl.searchParams.append("format", "json");
    recentTracksUrl.searchParams.append("limit", "10");

    const topTracksUrl = new URL(LASTFM_BASE_URL);
    topTracksUrl.searchParams.append("method", "user.gettoptracks");
    topTracksUrl.searchParams.append("user", lastfmUsername);
    topTracksUrl.searchParams.append("api_key", LASTFM_API_KEY || "");
    topTracksUrl.searchParams.append("format", "json");
    topTracksUrl.searchParams.append("period", "7day");
    topTracksUrl.searchParams.append("limit", "5");

    const userInfoUrl = new URL(LASTFM_BASE_URL);
    userInfoUrl.searchParams.append("method", "user.getinfo");
    userInfoUrl.searchParams.append("user", lastfmUsername);
    userInfoUrl.searchParams.append("api_key", LASTFM_API_KEY || "");
    userInfoUrl.searchParams.append("format", "json");

    const [recentTracksRes, topTracksRes, userInfoRes] = await Promise.all([
      fetch(recentTracksUrl.toString()),
      fetch(topTracksUrl.toString()),
      fetch(userInfoUrl.toString()),
    ]);

    const [recentTracks, topTracks, userInfo] = await Promise.all([
      recentTracksRes.json(),
      topTracksRes.json(),
      userInfoRes.json(),
    ]);

    return NextResponse.json({
      recentTracks: recentTracks.recenttracks?.track || [],
      topTracks: topTracks.toptracks?.track || [],
      userInfo: userInfo.user || {},
      username: lastfmUsername,
    });
  } catch (error) {
    console.error("Last.fm API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch Last.fm data" },
      { status: 500 }
    );
  }
}
