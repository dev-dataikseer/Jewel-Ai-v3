/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', "Segoe UI", "system-ui", "sans-serif"],
      },
      colors: {
        jewel: {
          bg: "var(--jewel-bg)",
          surface: "var(--jewel-surface)",
          muted: "var(--jewel-surface-muted)",
          ink: "var(--jewel-ink)",
          "ink-muted": "var(--jewel-ink-muted)",
          border: "var(--jewel-border)",
          accent: "var(--jewel-accent)",
          "accent-hover": "var(--jewel-accent-hover)",
          "accent-soft": "var(--jewel-accent-soft)",
          metal: "var(--jewel-metal)",
          success: "var(--jewel-success)",
          warning: "var(--jewel-warning)",
          danger: "var(--jewel-danger)",
        },
      },
      borderRadius: {
        jewel: "var(--jewel-radius-md)",
        "jewel-sm": "var(--jewel-radius-sm)",
        "jewel-lg": "var(--jewel-radius-lg)",
      },
      boxShadow: {
        soft: "var(--jewel-shadow-sticky)",
        sticky: "var(--jewel-shadow-sticky)",
      },
    },
  },
  plugins: [],
};
