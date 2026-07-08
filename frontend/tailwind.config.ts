import type { Config } from "tailwindcss";
import colors from "tailwindcss/colors";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand accent — swap this one line to re-theme the whole app.
        brand: colors.emerald,
        // Deep-teal surface for the match panel on job cards.
        panel: colors.teal,
      },
    },
  },
  plugins: [],
};

export default config;
