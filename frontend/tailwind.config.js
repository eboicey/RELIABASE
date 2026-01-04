/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0f172a",
          800: "#111827",
          700: "#1e293b",
          600: "#334155",
          500: "#475569",
        },
        accent: {
          500: "#22c55e",
          400: "#34d399",
          300: "#a7f3d0",
        },
      },
      fontFamily: {
        display: ["'Space Grotesk'", "Inter", "system-ui", "sans-serif"],
        body: ["'Inter'", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
