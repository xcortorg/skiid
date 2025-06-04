import { db } from "@/lib/db";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { NextResponse } from "next/server";
import { Session } from "next-auth";

function roundToInterval(date: Date, step: number): number {
  return Math.floor(date.getTime() / step) * step;
}

function generateTimePoints(period: string, startDate: Date): [Date[], number] {
  const points: Date[] = [];
  const now = new Date();
  let interval: number;
  let step: number;

  switch (period) {
    case "24h":
      interval = 24;
      step = 60 * 60 * 1000;
      break;
    case "7d":
      interval = 7 * 24;
      step = 60 * 60 * 1000;
      break;
    case "30d":
      interval = 30;
      step = 24 * 60 * 60 * 1000;
      break;
    case "6mo":
      interval = 180;
      step = 24 * 60 * 60 * 1000;
      break;
    case "12mo":
      interval = 365;
      step = 24 * 60 * 60 * 1000;
      break;
    default:
      interval = 30;
      step = 24 * 60 * 60 * 1000;
  }

  for (let i = 0; i < interval; i++) {
    points.push(new Date(now.getTime() - (interval - 1 - i) * step));
  }

  return [points, step] as const;
}

export async function GET(request: Request) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const period = searchParams.get("period") || "30d";

    const startDate = new Date();
    switch (period) {
      case "24h":
        startDate.setHours(startDate.getHours() - 24);
        break;
      case "7d":
        startDate.setDate(startDate.getDate() - 7);
        break;
      case "30d":
        startDate.setDate(startDate.getDate() - 30);
        break;
      case "6mo":
        startDate.setMonth(startDate.getMonth() - 6);
        break;
      case "12mo":
        startDate.setMonth(startDate.getMonth() - 12);
        break;
    }

    const userTokens = await db.apiToken.findMany({
      where: { userId: session.user.id },
      select: { id: true },
    });
    const tokenIds = userTokens.map((token) => token.id);

    const baseWhere = {
      tokenId: { in: tokenIds },
      timestamp: { gte: startDate },
    };

    const [
      totalRequests,
      avgResponseTime,
      statusCodeStats,
      endpointStats,
      requestsOverTime,
      errorStats,
      cpuStats,
    ] = await Promise.all([
      db.apiTokenStat.count({
        where: baseWhere,
      }),

      db.apiTokenStat.aggregate({
        where: baseWhere,
        _avg: { duration: true },
      }),

      db.apiTokenStat.groupBy({
        where: baseWhere,
        by: ["statusCode"],
        _count: true,
      }),

      db.apiTokenStat.groupBy({
        where: baseWhere,
        by: ["endpoint"],
        _count: true,
        _avg: { duration: true },
      }),

      db.apiTokenStat.groupBy({
        where: baseWhere,
        by: ["timestamp"],
        _count: true,
        orderBy: { timestamp: "asc" },
      }),

      db.apiTokenStat.findMany({
        where: {
          ...baseWhere,
          errorMessage: { not: null },
        },
        select: {
          errorMessage: true,
        },
      }),

      db.apiTokenStat.aggregate({
        where: baseWhere,
        _avg: { cpuTime: true },
      }),
    ]);

    const errorCount = statusCodeStats.reduce(
      (acc, stat) => (stat.statusCode >= 400 ? acc + stat._count : acc),
      0,
    );
    const errorRate = totalRequests > 0 ? errorCount / totalRequests : 0;

    const [timePoints, step] = generateTimePoints(period, startDate);
    const requestsByTimestamp = new Map();
    requestsOverTime.forEach((point) => {
      const roundedTime = roundToInterval(point.timestamp, step);
      requestsByTimestamp.set(
        roundedTime,
        (requestsByTimestamp.get(roundedTime) || 0) + point._count,
      );
    });

    const requestsOverTimeFormatted = timePoints.map((date) => ({
      timestamp: date.toISOString(),
      count: requestsByTimestamp.get(roundToInterval(date, step)) || 0,
    }));

    const errorCounts: Record<string, number> = {};
    errorStats.forEach((error) => {
      if (error.errorMessage) {
        errorCounts[error.errorMessage] =
          (errorCounts[error.errorMessage] || 0) + 1;
      }
    });

    const topErrors = Object.entries(errorCounts)
      .map(([message, count]) => ({ message, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    return NextResponse.json({
      totalRequests,
      averageResponseTime: avgResponseTime._avg.duration || 0,
      errorRate,
      cpuUsage: (cpuStats._avg.cpuTime || 0) * 100,

      endpointStats: endpointStats
        .map((stat) => ({
          endpoint: stat.endpoint,
          count: stat._count,
          avgDuration: stat._avg.duration || 0,
        }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10),

      statusCodes: statusCodeStats.map((stat) => ({
        code: stat.statusCode,
        count: stat._count,
      })),

      requestsOverTime: requestsOverTimeFormatted,
      topErrors,
    });
  } catch (error) {
    console.error("Error fetching API analytics:", error);
    return NextResponse.json(
      { error: "Failed to fetch analytics data" },
      { status: 500 },
    );
  }
}
