/**
 * Tailwind 4 JS configuration (H.1.3).
 *
 * In Tailwind 4 the JS config file is optional — `@theme` blocks in CSS
 * can declare tokens directly. We keep this file because the guide
 * (H.1.3, H.2.1) treats `tailwind.config.cjs` as the single source of
 * truth for design tokens. The entry CSS files reference this file via
 * `@config "../../tailwind.config.cjs";` in `_base.css`.
 *
 * Notes specific to v4:
 * - Container queries are built into Tailwind 4 (`@container` works
 *   without a plugin). The legacy `@tailwindcss/container-queries`
 *   plugin is intentionally not loaded here.
 * - `@tailwindcss/forms` and `@tailwindcss/typography` remain external
 *   plugins, pinned to v4-compatible 0.5.x releases.
 * - Browser support: Safari 16.4+, Chrome 111+, Firefox 128+ (v4 baseline).
 */
module.exports = {
  content: [
    "../backend/apps/**/templates/**/*.html",
    "../backend/templates/**/*.html",
    "./src/**/*.{ts,js}",
    "./index.html",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        surface: {
          canvas: "#f8fafc",
          raised: "#ffffff",
          sunken: "#f1f5f9",
          border: "#e2e8f0",
          "border-strong": "#cbd5e1",
        },
        text: {
          DEFAULT: "#0f172a",
          muted: "#475569",
          subtle: "#64748b",
          inverse: "#f8fafc",
        },
        status: {
          success: "#16a34a",
          "success-soft": "#dcfce7",
          warning: "#d97706",
          "warning-soft": "#fef3c7",
          danger: "#dc2626",
          "danger-soft": "#fee2e2",
          info: "#2563eb",
          "info-soft": "#dbeafe",
        },
        sidebar: {
          DEFAULT: "#0f172a",
          hover: "#1e293b",
          muted: "#94a3b8",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "monospace",
        ],
      },
      borderRadius: {
        "mph-xl": "0.75rem",
        "mph-2xl": "1rem",
        "mph-3xl": "1.5rem",
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
    // @tailwindcss/container-queries intentionally NOT included —
    // container queries are built into Tailwind 4.
  ],
};