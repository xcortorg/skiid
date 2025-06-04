const CF_API_TOKEN = process.env.CLOUDFLARE_API_TOKEN;
const CF_ZONE_ID =
  process.env.CLOUDFLARE_ZONE_ID || "7ccae135639d8f86069ed29842e2ba7d";
const CF_API_BASE = "https://api.cloudflare.com/client/v4";

export interface CloudflareResponse<T> {
  result: T;
  success: boolean;
  errors: any[];
  messages: any[];
}

export interface CustomHostname {
  id: string;
  hostname: string;
  ssl: {
    status: string;
    method: string;
    validation_records?: Array<{
      txt_name?: string;
      txt_value?: string;
    }>;
  };
  status: string;
  verification_errors?: string[];
  ownership_verification?: {
    type: string;
    name: string;
    value: string;
  };
  created_at: string;
}

export async function cfRequest<T>(
  endpoint: string,
  method: string = "GET",
  data?: any,
): Promise<CloudflareResponse<T>> {
  const url = `${CF_API_BASE}${endpoint}`;

  const headers = {
    Authorization: `Bearer ${CF_API_TOKEN}`,
    "Content-Type": "application/json",
  };

  const options: RequestInit = {
    method,
    headers,
    body: data ? JSON.stringify(data) : undefined,
  };

  const response = await fetch(url, options);
  const result = await response.json();

  if (!response.ok) {
    console.error("Cloudflare API error:", result);
    throw new Error(
      result.errors?.[0]?.message || "Cloudflare API request failed",
    );
  }

  return result;
}

export async function createCustomHostname(
  hostname: string,
): Promise<CustomHostname> {
  const data = {
    hostname,
    ssl: {
      method: "txt",
      type: "dv",
      settings: {
        min_tls_version: "1.2",
      },
    },
  };

  const response = await cfRequest<CustomHostname>(
    `/zones/${CF_ZONE_ID}/custom_hostnames`,
    "POST",
    data,
  );

  return response.result;
}

export async function getCustomHostnames(): Promise<CustomHostname[]> {
  const response = await cfRequest<CustomHostname[]>(
    `/zones/${CF_ZONE_ID}/custom_hostnames`,
  );

  return response.result;
}

export async function getCustomHostname(
  identifier: string,
): Promise<CustomHostname> {
  const response = await cfRequest<CustomHostname>(
    `/zones/${CF_ZONE_ID}/custom_hostnames/${identifier}`,
  );

  return response.result;
}

export async function updateCustomHostname(
  identifier: string,
  data: any,
): Promise<CustomHostname> {
  const response = await cfRequest<CustomHostname>(
    `/zones/${CF_ZONE_ID}/custom_hostnames/${identifier}`,
    "PATCH",
    data,
  );

  return response.result;
}

export async function deleteCustomHostname(
  identifier: string,
): Promise<{ id: string }> {
  const response = await cfRequest<{ id: string }>(
    `/zones/${CF_ZONE_ID}/custom_hostnames/${identifier}`,
    "DELETE",
  );

  return response.result;
}

export async function findHostnameIdentifier(
  hostname: string,
): Promise<string | null> {
  try {
    const hostnames = await getCustomHostnames();
    const found = hostnames.find((h) => h.hostname === hostname);
    return found ? found.id : null;
  } catch (error) {
    console.error("Error finding hostname:", error);
    return null;
  }
}
