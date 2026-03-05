import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)"]
      },
      fontSize: {
        "display-1": ["2.5rem", { lineHeight: "1.2", fontWeight: "700" }],
        "display-2": ["2rem", { lineHeight: "1.25", fontWeight: "700" }],
        "display-3": ["1.5rem", { lineHeight: "1.3", fontWeight: "700" }],
        "display-4": ["1.25rem", { lineHeight: "1.35", fontWeight: "700" }],
        "display-5": ["1.125rem", { lineHeight: "1.4", fontWeight: "700" }],
        "display-6": ["1rem", { lineHeight: "1.45", fontWeight: "700" }],
        "heading-1": ["1.75rem", { lineHeight: "1.2", fontWeight: "600" }],
        "heading-2": ["1.5rem", { lineHeight: "1.25", fontWeight: "600" }],
        "heading-3": ["1.25rem", { lineHeight: "1.3", fontWeight: "600" }],
        "heading-4": ["1.125rem", { lineHeight: "1.35", fontWeight: "600" }],
        "heading-5": ["1rem", { lineHeight: "1.4", fontWeight: "600" }],
        "heading-6": ["0.875rem", { lineHeight: "1.45", fontWeight: "600" }],
        "body-xs": ["0.625rem", { lineHeight: "1.5", fontWeight: "400" }],
        "body-sm": ["0.75rem", { lineHeight: "1.5", fontWeight: "400" }],
        "body-md": ["0.8125rem", { lineHeight: "1.5", fontWeight: "400" }],
        "body-lg": ["0.875rem", { lineHeight: "1.6", fontWeight: "400" }],
        "body-xl": ["1rem", { lineHeight: "1.6", fontWeight: "400" }]
      },
      colors: {
        bg: "rgb(var(--color-bg) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        "surface-2": "rgb(var(--color-surface-2) / <alpha-value>)",
        primary: "rgb(var(--color-primary) / <alpha-value>)",
        "primary-soft": "rgb(var(--color-primary-soft) / <alpha-value>)",
        text: "rgb(var(--color-text) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        "muted-soft": "rgb(var(--color-muted-soft) / <alpha-value>)",
        border: "rgb(var(--color-border) / <alpha-value>)"
      },
      spacing: {
        1: "var(--space-1)",
        2: "var(--space-2)",
        3: "var(--space-3)",
        4: "var(--space-4)",
        5: "var(--space-5)",
        6: "var(--space-6)",
        8: "var(--space-7)",
        10: "var(--space-8)",
        12: "var(--space-9)"
      },
      borderRadius: {
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)"
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)"
      }
    }
  },
  plugins: []
};

export default config;
