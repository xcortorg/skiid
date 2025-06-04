import { Redis } from '@upstash/redis';

if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
  throw new Error("Missing UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN");
}

export const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

export async function getCachedData<T>(key: string): Promise<T | null> {
  try {
    const data = await redis.get(key);
    return data && typeof data === 'string' ? JSON.parse(data) : null;
  } catch (error) {
    console.error("Redis get error:", error);
    return null;
  }
}

export async function setCachedData(
  key: string,
  value: any,
  expirationInSeconds?: number
): Promise<void> {
  try {
    const serializedValue = JSON.stringify(value);
    if (expirationInSeconds) {
      await redis.set(key, serializedValue, { ex: expirationInSeconds });
    } else {
      await redis.set(key, serializedValue);
    }
  } catch (error) {
    console.error("Redis set error:", error);
  }
}

export async function deleteCachedData(key: string): Promise<void> {
  try {
    await redis.del(key);
  } catch (error) {
    console.error("Redis delete error:", error);
  }
}

export async function incrementCounter(
  key: string,
  expirationInSeconds: number
): Promise<number> {
  try {
    const count = await redis.incr(key);
    if (count === 1) {
      await redis.expire(key, expirationInSeconds);
    }
    return count;
  } catch (error) {
    console.error("Redis increment error:", error);
    return 0;
  }
}
