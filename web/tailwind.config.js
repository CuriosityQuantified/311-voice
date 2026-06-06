/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nyc: {
          blue: '#0047AB',
          orange: '#FF6B35',
          dark: '#1a1a2e',
          light: '#f5f5f5',
        }
      }
    },
  },
  plugins: [],
}
