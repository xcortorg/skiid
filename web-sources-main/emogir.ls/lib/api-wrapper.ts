import { httpRequestsTotal, httpRequestDuration } from "@/lib/metrics";
import { headers } from "next/headers";

export function withMetrics<
  T extends (req: Request, ...args: any[]) => Promise<Response>,
>(handler: T): typeof handler {
  return async function (req: Request, ...args: any[]) {
    const headersList = await headers();
    const requestStart = headersList.get("x-request-start");
    const start = requestStart ? parseInt(requestStart) : Date.now();

    try {
      const response = await handler(req, ...args);

      const method = req.method;
      const url = new URL(req.url);
      const route = url.pathname;
      const statusCode = response.status.toString();

      let userId = "anonymous";

      const userIdHeader = response.headers.get("x-user-id");
      if (userIdHeader) {
        userId = userIdHeader;
      }

      httpRequestsTotal.inc({
        method,
        route,
        status_code: statusCode,
        user_id: userId,
      });
      httpRequestDuration.observe(
        { method, route, status_code: statusCode, user_id: userId },
        (Date.now() - start) / 1000,
      );

      return response;
    } catch (error) {
      const method = req.method;
      const url = new URL(req.url);
      const route = url.pathname;
      const statusCode = "500";

      httpRequestsTotal.inc({
        method,
        route,
        status_code: statusCode,
        user_id: "anonymous",
      });
      httpRequestDuration.observe(
        { method, route, status_code: statusCode, user_id: "anonymous" },
        (Date.now() - start) / 1000,
      );

      throw error;
    }
  } as T;
}
