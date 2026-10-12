// Solo hace falta si cambiás clases en las plantillas. Regenerá public/tw.css con:
//   npx tailwindcss@3.4.17 -i styles.css -o public/tw.css --minify
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: { extend: { colors: {
    bg: "#0b0b1a", card: "#15152b", line: "#26264a", brand: "#7c5cff", brand2: "#3b82f6", pinky: "#ec4899",
  } } },
};
