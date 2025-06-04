import { db } from "@/lib/db";
import { incrementCounter } from "@/lib/redis";
import { getEndpointRateLimit } from "@/lib/rate-limits";
import { NextResponse } from "next/server";
import crypto from "crypto";

export async function validateApiKey(request: Request) {
  try {
    const authHeader = request.headers.get("authorization");
    if (!authHeader?.startsWith("Bearer ")) {
      console.log("No Bearer token found");
      return null;
    }

    const rawToken = authHeader.substring(7).trim();
    const hashedToken = crypto
      .createHash("sha256")
      .update(rawToken)
      .digest("hex");

    const apiToken = await db.apiToken.findFirst({
      where: {
        token: hashedToken,
        isActive: true,
        OR: [{ expiresAt: null }, { expiresAt: { gt: new Date() } }],
      },
      include: {
        user: true,
      },
    });

    if (!apiToken) {
      console.log("No valid token found in database");
      return null;
    }

    const rateLimitKey = `rate_limit:${apiToken.id}:${request.url}`;
    const rateLimit = getEndpointRateLimit(request.url);

    const currentCount = await incrementCounter(rateLimitKey, rateLimit.window);

    if (currentCount > (apiToken.rateLimit || rateLimit.requests)) {
      throw new Error("Rate limit exceeded");
    }

    await db.apiToken.update({
      where: { id: apiToken.id },
      data: { lastUsed: new Date() },
    });

    return apiToken;
  } catch (error) {
    console.error("Token validation error:", error);
    return null;
  }
}

export async function withApiAuth(
  request: Request,
  handler: (apiToken: any) => Promise<Response>,
) {
  const startTime = Date.now();
  const startUsage = process.cpuUsage();
  const startMemory = process.memoryUsage();
  let apiToken: any = null;

  try {
    apiToken = await validateApiKey(request);
    if (!apiToken) {
      return NextResponse.json({ error: "Invalid API key" }, { status: 401 });
    }

    const response = await handler(apiToken);

    const cpuUsage = process.cpuUsage(startUsage);
    const cpuTimeMs = (cpuUsage.user + cpuUsage.system) / 1000;
    const memoryUsed = process.memoryUsage().heapUsed - startMemory.heapUsed;

    const url = new URL(request.url);
    const userAgent = request.headers.get("user-agent");
    const ipAddress = request.headers.get("x-forwarded-for") || "unknown";

    const responseSize = Number(response.headers.get("content-length")) || 0;
    const cacheHit = response.headers.get("x-cache") === "HIT";

    const queryParams: Record<string, string> = {};
    url.searchParams.forEach((value, key) => {
      queryParams[key] = value;
    });

    await db.apiTokenStat.create({
      data: {
        tokenId: apiToken.id,
        endpoint: url.pathname,
        method: request.method,
        statusCode: response.status,
        duration: Date.now() - startTime,

        userAgent,
        ipAddress,

        responseSize,
        cacheHit,

        cpuTime: cpuTimeMs,
        memoryUsage: memoryUsed,

        queryParams,

        metadata: {
          headers: Object.fromEntries(request.headers),
          timestamp: new Date().toISOString(),
        },
      },
    });

    return response;
  } catch (error) {
    const errorResponse =
      error instanceof Error && error.message === "Rate limit exceeded"
        ? NextResponse.json(
            {
              error: "Rate limit exceeded",
              message: "Too many requests, please try again later",
            },
            {
              status: 429,
              headers: {
                "Retry-After": "3600",
              },
            },
          )
        : NextResponse.json(
            { error: "Internal server error" },
            { status: 500 },
          );

    if (error instanceof Error && apiToken) {
      await db.apiTokenStat.create({
        data: {
          tokenId: apiToken.id,
          endpoint: new URL(request.url).pathname,
          method: request.method,
          statusCode: errorResponse.status,
          duration: Date.now() - startTime,
          errorMessage: error.message,
          errorCode: error.name,
        },
      });
    }

    return errorResponse;
  }
}
