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
        'light-bg': '#f3f3f3ff',
        'light-panel': '#e2e7edff',
        'light-text': '#1a2332',
        'light-text-dim': '#5a6c84',
        'light-border': '#d0dae8',
        'light-accent': '#2563eb',
        
        'dark-bg': '#1b1d1fff',
        'dark-panel': '#1f2531ff',
        'dark-text': '#e6ecf5',
        'dark-text-dim': '#8c9db5',
        'dark-border': '#213c5eff',
        'dark-accent': '#3b82f6',
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
