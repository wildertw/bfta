# Bells Fork Site Build Instructions

This repository contains the static website for Bells Fork Auto & Truck.

## Development

- The site is purely HTML/CSS/JS. Edit files under the root.
- Add new vehicles by editing `inventory.json` or using the admin UI.

### Linting & Formatting

Make sure you have Node.js installed. Then run:

```powershell
npm install
npm run lint       # ESLint will fix simple issues
npm run format     # Prettier will format files
```

### Building for Production

To create minified, production-ready assets:

```powershell
npm run build
```

This will produce:

- `assets/js/bundle.min.js` — bundled & minified JS (utils, inventory-loader, etc.)
- `style.min.css` — minified CSS

The HTML pages include comments showing where to swap the development includes for these minified files. Simply replace the unminified `<script>`/`<link>` lines with the `.min` versions before deploying.

## Tools

- `esbuild` is used for JS bundling/minification
- `clean-css-cli` is used for CSS minification
- ESLint + Prettier enforce consistent style

Feel free to extend or modify the build process as needed.