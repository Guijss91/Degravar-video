/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        'defensoria': {
          50: '#f0f9f4',
          100: '#dcf4e5',
          200: '#bbe7ce',
          300: '#8dd4ad',
          400: '#5bb985',
          500: '#369e64',
          600: '#26804f',
          700: '#1f6b42',
          800: '#1a5437',
          900: '#16442f',
          950: '#147235', // Cor principal institucional
        }
      }
    },
  },
  plugins: [],
}
