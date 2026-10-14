/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        sider: {
          DEFAULT: "var(--sider)",
          hover: "var(--sider-hover)",
          active: "var(--primary)",
        },
        panel: {
          bg: "var(--panel-bg)",
          card: "var(--card)",
          border: "var(--border)",
          muted: "var(--muted)",
          text: "var(--text)",
          line: "var(--input-border)",
          soft: "var(--soft-bg)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          hover: "var(--primary-hover)",
          soft: "var(--primary-soft)",
        },
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        header: "var(--header-bg)",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          '"Helvetica Neue"',
          "Arial",
          "sans-serif",
        ],
        mono: ["SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "var(--shadow-card)",
        popup: "var(--shadow-popup)",
      },
      borderRadius: {
        ant: "8px",
      },
    },
  },
  plugins: [],
};
