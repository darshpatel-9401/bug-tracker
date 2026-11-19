/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f5f1ea",
        card: "#fffdf9",
        ink: "#1d1b18",
        muted: "#6f695f",
        line: "#ddd5c8",
        signal: "#e5501b",
        "signal-dark": "#c23f10",
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
