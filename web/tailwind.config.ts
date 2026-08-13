import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "var(--paper)",
        card: "var(--card)",
        ink: "var(--ink)",
        "ink-dim": "var(--ink-dim)",
        line: "var(--line)",
        "line-strong": "var(--line-strong)",
        accent: {
          DEFAULT: "var(--accent)",
          deep: "var(--accent-deep)",
          wash: "var(--accent-wash)",
        },
        signal: {
          DEFAULT: "var(--signal)",
          wash: "var(--signal-wash)",
        },
        status: {
          good: "var(--status-good)",
          "good-wash": "var(--status-good-wash)",
          warning: "var(--status-warning)",
          "warning-wash": "var(--status-warning-wash)",
          critical: "var(--status-critical)",
          "critical-wash": "var(--status-critical-wash)",
        },
      },
      fontFamily: {
        sans: ["-apple-system", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["ui-monospace", "SF Mono", "Cascadia Code", "Consolas", "monospace"],
      },
      borderRadius: {
        card: "10px",
      },
    },
  },
  plugins: [],
};

export default config;
