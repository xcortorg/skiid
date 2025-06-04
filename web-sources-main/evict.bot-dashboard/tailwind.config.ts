import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'evict': {
          '100': '#141114',
          '200': '#111212',
          '300': '#161717',
          '400': '#161717',
          '500': '#1B1C1C',
          '600': '#111212',
          '700': '#6b6b6b',
          'pink': '#94A8AE',
          'border': '#0f0f0e',
          'card-border': '#232424',
          'secondary': '#919191',
          'dim': '#1c1c1c',
          'discord': '#5968de',
        }
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
    },
  },
  plugins: [],
};
export default config;