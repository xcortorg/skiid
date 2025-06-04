import type { Config } from "tailwindcss"

const config: Config = {
    content: [
        "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}"
    ],
    theme: {
        extend: {
            colors: {
                bleed: {
                    '100': '#141114',
                    '200': '#141314',
                    '300': '#292929',
                    '400': '#262226',
                    '500': '#262226',
                    '600': '#716f71',
                    '700': '#262226',
                    'border': '#0f0f0e',
                    'pink': '#c5b3c0',
                    'dim': '#1c1c1c',
                    'discord': '#5968de',
                    'black': '#000000',
                    unselected: "#A2A2A2",
                    main: "#93bddb",
                    "card-border": "#232424",
                    secondary: "#919191",
                },
                generic: {
                    '100': '#141114',
                    '200': '#141314',
                    '300': '#292929',
                    '400': '#262226',
                    '500': '#605f60',
                    '600': '#716f71',
                    '700': '#827f82',
                    'border': '#0f0f0e',
                    'pink': '#c5b3c0',
                    'dim': '#1c1c1c',
                    'discord': '#5968de',
                    'black': '#000000'
                }
            },
            animation: {
                glow: "glow 1.5s ease-in-out infinite"
            }
        }
    },
    plugins: []
}
export default config
