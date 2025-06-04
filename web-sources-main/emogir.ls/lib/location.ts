interface LocationInfo {
  city: string;
  country: string;
}

export async function getIpLocation(ip: string): Promise<LocationInfo | null> {
  if (ip === "::1" || ip === "127.0.0.1" || ip === "unknown") {
    return {
      city: "Local",
      country: "Development",
    };
  }

  try {
    const response = await fetch(`https://ipapi.co/${ip}/json/`);
    const data = await response.json();

    if (data.error) {
      console.error("IP location error:", data.reason);
      return null;
    }

    return {
      city: data.city || "Unknown",
      country: data.country_name || "Unknown",
    };
  } catch (error) {
    console.error("IP location error:", error);
    return null;
  }
}
