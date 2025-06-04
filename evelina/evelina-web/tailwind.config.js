/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Manrope', 'sans-serif'],
      },
      colors: {
        primary: '#FFFFFF',
        secondary: '#999999',
        tertiary: '#a8a8a8',
        'gray-custom': '#666666',
        'dark-1': '#282828',
        'dark-2': '#181818',
        'dark-3': '#151515',
        'dark-4': '#111111',
        'dark-5': '#181818',
        'dark-blue': '#000000',
        'theme': '#729bb0',
      },
      backgroundImage: {
        'gradient-custom': 'linear-gradient(45deg, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
};