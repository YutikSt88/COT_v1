import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0b0f14",
        foreground: "#d7dde5",
        panel: "#11161d",
        border: "#242c36",
        muted: "#8a98a9",
        bullish: "#22c55e",
        bearish: "#ef4444",
        warning: "#f59e0b",
        neutral: "#38bdf8",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["Roboto Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
