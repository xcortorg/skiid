export const API_RATE_LIMITS = {
  DEFAULT: {
    requests: 1000,
    window: 60 * 60,
  },
  ENDPOINTS: {
    "/api/v1/links": {
      requests: 900,
      window: 60 * 60,
    },
    "/api/v1/profile": {
      requests: 900,
      window: 60 * 60,
    },
    "/api/v1/appearance": {
      requests: 900,
      window: 60 * 60,
    },
    "/api/v1/auth/token": {
      requests: 30,
      window: 60 * 60,
    },
  },
} as const;

export function getEndpointRateLimit(path: string) {
  const normalizedPath = path.split("?")[0];

  const genericPath = normalizedPath.replace(/\/api\/v1\/[^\/]+\//, "/api/v1/");

  for (const [pattern, limit] of Object.entries(API_RATE_LIMITS.ENDPOINTS)) {
    if (genericPath.startsWith(pattern)) {
      return limit;
    }
  }

  return API_RATE_LIMITS.DEFAULT;
}
