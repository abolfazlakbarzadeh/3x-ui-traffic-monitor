/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f1c18",
        mist: "#e7f0ec",
        leaf: "#1f6f54",
        clay: "#c45c26",
        line: "#c5d4cc",
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "Segoe UI", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
