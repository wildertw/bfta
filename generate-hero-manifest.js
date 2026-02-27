#!/usr/bin/env node
/**
 * Generates assets/hero/manifest.json by scanning the assets/hero folder
 * for image files. Works great for Netlify/Git deploys.
 *
 * Usage:
 *   node generate-hero-manifest.js
 */

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const HERO_DIR = path.join(ROOT, 'assets', 'hero');
const OUT_PATH = path.join(HERO_DIR, 'manifest.json');

const IMAGE_EXTS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif']);

function isImageFile(name) {
  const ext = path.extname(name).toLowerCase();
  return IMAGE_EXTS.has(ext);
}

function safeJsonStringify(obj) {
  return JSON.stringify(obj, null, 2) + '\n';
}

(async function main() {
  try {
    if (!fs.existsSync(HERO_DIR)) {
      process.exit(0);
    }

    const entries = await fs.promises.readdir(HERO_DIR, { withFileTypes: true });
    const files = entries
      .filter((e) => e.isFile())
      .map((e) => e.name)
      .filter((name) => name !== 'manifest.json')
      .filter(isImageFile)
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));

    const manifest = {
      generatedAt: new Date().toISOString(),
      images: files
    };

    await fs.promises.writeFile(OUT_PATH, safeJsonStringify(manifest), 'utf8');
  } catch (err) {
    console.error('[hero-manifest] Error:', err);
    process.exit(1);
  }
})();
