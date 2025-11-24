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
        // Light mode colors - softer with blue tint
        'light-bg': '#e8eef5',
        'light-panel': '#f4f7fb',
        'light-text': '#1a2332',
        'light-text-dim': '#5a6c84',
        'light-border': '#d0dae8',
        
        // Dark mode colors - with blue undertone
        'dark-bg': '#0a0e14',
        'dark-panel': '#131821',
        'dark-text': '#e6ecf5',
        'dark-text-dim': '#8c9db5',
        'dark-border': '#1e2936',
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
