/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",        // Global templates
    "./apps/**/templates/**/*.html", // App-specific templates
    "./static/js/**/*.js",           // Any custom JS
  ],
  theme: {
    extend: {
      colors: {
        'buk-red': '#880000', // Example BUK branding color
      }
    },
  },
  plugins: [],
}