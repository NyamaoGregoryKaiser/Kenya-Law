/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Kenya Law Reports - Official Brand Colors
        'legal-maroon': '#7A1F33',        // Deep Maroon - Primary/Headers
        'legal-maroon-dark': '#5C1727',   // Darker maroon for hover states
        'legal-maroon-light': '#F5E8EB',  // Light maroon tint
        'legal-gold': '#D9A12D',          // Golden Amber - Accent/Buttons
        'legal-gold-dark': '#B8861F',     // Darker gold for hover
        'legal-gold-light': '#FDF6E3',    // Light gold tint
        'legal-text': '#232323',          // Dark charcoal - Main text
        'legal-text-muted': '#5A5A5A',    // Muted text
        'legal-bg': '#FAFAFA',            // Off-white background
        'legal-white': '#FFFFFF',         // Pure white
        'legal-border': '#E2E2E2',        // Light border color
        'legal-border-dark': '#CCCCCC',   // Darker border
        // Keep Kenya flag colors for national identity elements
        'kenya-black': '#000000',
        'kenya-red': '#BB0000',
        'kenya-green': '#006400',
        'kenya-white': '#FFFFFF',
      },
      fontFamily: {
        'serif': ['Merriweather', 'Georgia', 'serif'],
        'sans': ['Source Sans Pro', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'legal-gradient': 'linear-gradient(135deg, #7A1F33 0%, #5C1727 100%)',
        'gold-gradient': 'linear-gradient(135deg, #D9A12D 0%, #B8861F 100%)',
      },
      boxShadow: {
        'legal': '0 4px 20px rgba(122, 31, 51, 0.08)',
        'legal-lg': '0 10px 40px rgba(122, 31, 51, 0.12)',
        'gold': '0 4px 20px rgba(217, 161, 45, 0.15)',
      },
    },
  },
  plugins: [],
}
