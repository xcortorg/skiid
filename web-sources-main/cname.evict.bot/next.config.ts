import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/:path*",
          destination: "/api/resolve/:path*",
        },
      ],
      afterFiles: [],
      fallback: []
    };
  },
  domains: [
    {
      domain: "cname.evict.bot",
      defaultLocale: "en",
    },
  ],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
};

export default nextConfig;
