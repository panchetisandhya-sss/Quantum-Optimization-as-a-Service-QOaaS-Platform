/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#050505",
        card: "#111111",
        primary: {
          DEFAULT: "#6366F1",
          light: "#818CF8",
        },
        secondary: {
          DEFAULT: "#8B5CF6",
        },
        success: {
          DEFAULT: "#10B981",
        },
        accent: {
          DEFAULT: "#38BDF8",
        },
        "dark-bg": "#050505",
        "dark-card": "#111111",
        "dark-border": "#222222",
        "dark-hover": "#161616",
        "gray-850": "#222222",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        space: ["var(--font-space)", "sans-serif"],
        plex: ["var(--font-plex)", "monospace"],
      },
    },
  },
  plugins: [],
};

