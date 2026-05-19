/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        trunk: '#f59e0b',
        side: '#60a5fa',
        prereq: '#a78bfa',
        seealso: '#34d399',
      },
    },
  },
  plugins: [],
};
