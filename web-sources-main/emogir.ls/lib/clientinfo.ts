"use server";

import { headers } from "next/headers";
import { UAParser } from "ua-parser-js";

export async function getClientInfo() {
  const headersList = await headers();
  const parser = new UAParser();
  parser.setUA(headersList.get("user-agent") || "");

  const browser = parser.getBrowser();
  const os = parser.getOS();
  const device = parser.getDevice().type || "desktop";

  return {
    name: `${browser.name || "Unknown"} on ${os.name || "Unknown"}`,
    details: {
      browser: `${browser.name || "Unknown"} ${browser.version || ""}`,
      os: `${os.name || "Unknown"} ${os.version || ""}`,
      device: device,
    },
  };
}
