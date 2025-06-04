/** @type {import('next').NextConfig} */
const nextConfig = {
    compiler: {
        removeConsole: true,
      },
    swcMinify: true,
    webpack: (config, { buildId, dev, isServer, defaultLoaders, nextRuntime, webpack }) => {
    // Additional webpack configurations if needed
        return config;
    },
    async rewrites() {
        return [
            {
                source: "/",
                destination: "/index.html"
            }
        ]
    },
    images: {
        domains: ["i.imgur.com", "cdn..bot"]
    }
}

export default nextConfig
