/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    swcMinify: true,
    async redirects() {
        return [
            {
                source: '/discord',
                destination: 'https://discord.gg/evict',
                permanent: true,
            },
            {
                source: '/support',
                destination: 'https://discord.gg/evict',
                permanent: true,
            },
            {
                source: '/cmds',
                destination: '/commands',
                permanent: true,
            },
            {
                source: '/help',
                destination: '/commands',
                permanent: true,
            },
            {
                source: '/invite',
                destination: 'https://discordapp.com/oauth2/authorize?client_id=1203514684326805524&scope=bot+applications.commands&permissions=8',
                permanent: true,
            },
            {
                source: '/embeds',
                destination: 'https://embeds.evict.bot',
                permanent: true,
            },
            {
                source: '/docs',
                destination: 'https://docs.evict.bot',
                permanent: true,
            },
            {
                source: '/variables',
                destination: 'https://docs.evict.bot/embeds/variables',
                permanent: true,
            },
            {
                source: '/beta',
                destination: '/apply',
                permanent: true,
            }
        ]
    },
    async rewrites() {
        return [
            {
                source: '/',
                destination: '/index.html',
            },
        ];
    },
    images: {
        remotePatterns: [
            {
                protocol: 'https',
                hostname: '**',
            },
        ],
    },
};

export default nextConfig;
