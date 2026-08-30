/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: '#080C16',
          card: '#0F172A',
          cardHover: '#17233D',
          border: '#1E293B',
          borderLight: '#334155',
          emerald: '#10B981',
          emeraldDark: '#047857',
          cyan: '#06B6D4',
          blue: '#3B82F6',
          purple: '#8B5CF6',
          amber: '#F59E0B',
          rose: '#F43F5E',
          critical: '#EF4444',
          high: '#F97316',
          medium: '#FBBF24',
          low: '#10B981',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'glow-emerald': '0 0 20px -5px rgba(16, 185, 129, 0.4)',
        'glow-cyan': '0 0 20px -5px rgba(6, 182, 212, 0.4)',
        'glow-rose': '0 0 20px -5px rgba(244, 63, 94, 0.4)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
      }
    },
  },
  plugins: [],
}
