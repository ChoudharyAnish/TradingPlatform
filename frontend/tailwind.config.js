/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f2744",
        sea: "#0e7490",
        mist: "#e8eef5",
        sand: "#f7f5f1",
        alert: "#b45309",
        good: "#047857",
        bad: "#b91c1c",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        soft: "0 12px 40px rgba(15, 39, 68, 0.08)",
      },
    },
  },
  plugins: [],
};
