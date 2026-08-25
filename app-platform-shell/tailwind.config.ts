import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    // Sibling feature MFEs share this CSS bundle (host serves it).
    // Scanning their source ensures semantic classes used only inside
    // a feature still get emitted by Tailwind's tree-shake.
    "../feature-*-frontend/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--color-bg) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        "surface-muted": "rgb(var(--color-surface-muted) / <alpha-value>)",
        text: "rgb(var(--color-text) / <alpha-value>)",
        "text-muted": "rgb(var(--color-text-muted) / <alpha-value>)",
        border: "rgb(var(--color-border) / <alpha-value>)",
        primary: "rgb(var(--color-primary) / <alpha-value>)",
        "primary-fg": "rgb(var(--color-primary-fg) / <alpha-value>)",
        "primary-soft": "rgb(var(--color-primary-soft) / <alpha-value>)",
        "primary-soft-fg": "rgb(var(--color-primary-soft-fg) / <alpha-value>)",
        danger: "rgb(var(--color-danger) / <alpha-value>)",
        "danger-fg": "rgb(var(--color-danger-fg) / <alpha-value>)",
        "danger-soft": "rgb(var(--color-danger-soft) / <alpha-value>)",
        "danger-soft-fg": "rgb(var(--color-danger-soft-fg) / <alpha-value>)",
        success: "rgb(var(--color-success) / <alpha-value>)",
        "success-fg": "rgb(var(--color-success-fg) / <alpha-value>)",
        "success-soft": "rgb(var(--color-success-soft) / <alpha-value>)",
        "success-soft-fg": "rgb(var(--color-success-soft-fg) / <alpha-value>)",
        warning: "rgb(var(--color-warning) / <alpha-value>)",
        "warning-fg": "rgb(var(--color-warning-fg) / <alpha-value>)",
        "warning-soft": "rgb(var(--color-warning-soft) / <alpha-value>)",
        "warning-soft-fg": "rgb(var(--color-warning-soft-fg) / <alpha-value>)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      fontFamily: {
        sans: "var(--font-sans)",
        mono: "var(--font-mono)",
      },
    },
  },
  plugins: [],
};

export default config;
