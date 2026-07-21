/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', "Segoe UI", "system-ui", "sans-serif"],
        "jewel-mono": ["var(--jewel-font-mono)"],
      },
      colors: {
        jewel: {
          bg: "var(--jewel-bg)",
          "bg-admin": "var(--jewel-bg-admin)",
          surface: "var(--jewel-surface)",
          muted: "var(--jewel-surface-muted)",
          ink: "var(--jewel-ink)",
          "ink-muted": "var(--jewel-ink-muted)",
          "ink-faint": "var(--jewel-ink-faint)",
          border: "var(--jewel-border)",
          hairline: "var(--jewel-hairline)",
          accent: "var(--jewel-accent)",
          "accent-hover": "var(--jewel-accent-hover)",
          "accent-soft": "var(--jewel-accent-soft)",
          metal: "var(--jewel-metal)",
          precious: "var(--jewel-precious)",
          "precious-soft": "var(--jewel-precious-soft)",
          success: "var(--jewel-success)",
          warning: "var(--jewel-warning)",
          danger: "var(--jewel-danger)",
        },
      },
      borderRadius: {
        jewel: "var(--jewel-radius-md)",
        "jewel-md": "var(--jewel-radius-md)",
        "jewel-sm": "var(--jewel-radius-sm)",
        "jewel-lg": "var(--jewel-radius-lg)",
      },
      boxShadow: {
        soft: "var(--jewel-shadow-sticky)",
        sticky: "var(--jewel-shadow-sticky)",
        card: "var(--jewel-shadow-card)",
      },
    },
  },
  plugins: [],
};
