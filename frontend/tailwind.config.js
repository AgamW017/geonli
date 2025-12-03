/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'light-bg': '#f5f9fbff',
        'light-panel': '#e1eef2ff',
        'light-text': '#0f172a',
        'light-text-dim': '#475569',
        'light-border': '#b0daff',
        'light-accent': '#3375d2ff', // Blue
        'light-secondary': '#f85d0fff', // Orange
        
        'dark-bg': '#12111eff',
        'dark-panel': '#07113dff',
        'dark-text': '#f8fafcff',
        'dark-text-dim': '#94a3b8',
        'dark-border': '#0075beff',
        'dark-accent': '#3b82f6', // Blue
        'dark-secondary': '#ff5f0fff', // Orange
      },
      keyframes: {
        'fade-slide-in': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      },
      animation: {
        'fade-slide-in': 'fade-slide-in 0.5s ease-out forwards',
      }
    },
  },
  plugins: [],
}
