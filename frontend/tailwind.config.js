/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0A1020',
        surface: '#101A30',
        'surface-2': '#16223F',
        border: '#22305A',
        text: '#E6EDF7',
        'text-muted': '#93A4C3',
        accent: '#4C8DFF',
        'accent-soft': '#99CEFF',
        allow: '#22C55E',
        review: '#F5A524',
        block: '#EF4444',
        tier: {
          reproduced: '#EF4444',
          proven: '#F97316',
          inferred: '#EAB308',
          unknown: '#94A3B8',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'xs': ['12px', '16px'],
        'sm': ['14px', '20px'],
        'base': ['16px', '24px'],
        'lg': ['20px', '28px'],
        'xl': ['28px', '36px'],
        'verdict': ['40px', '48px'],
      },
      borderRadius: {
        'card': '12px',
        'input': '8px',
        'badge': '8px',
        'pill': '9999px',
      },
      spacing: {
        '4': '4px',
        '8': '8px',
        '12': '12px',
        '16': '16px',
        '24': '24px',
        '32': '32px',
        '48': '48px',
      },
      boxShadow: {
        'glow-allow': '0 0 24px -4px rgba(34, 197, 94, 0.25)',
        'glow-review': '0 0 24px -4px rgba(245, 165, 36, 0.25)',
        'glow-block': '0 0 24px -4px rgba(239, 68, 68, 0.25)',
      },
    },
  },
  plugins: [],
};
