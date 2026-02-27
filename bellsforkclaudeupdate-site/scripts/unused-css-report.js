#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const CSS_PATH = path.join(ROOT, 'style.css');

function readFiles(dir, exts, out = []) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name === '.git') continue;
      readFiles(p, exts, out);
    } else {
      if (exts.includes(path.extname(e.name).toLowerCase())) out.push(p);
    }
  }
  return out;
}

function parseCssSelectors(cssText) {
  const classSet = new Set();
  const idSet = new Set();
  // crude: split by '{' and parse selector lists
  const parts = cssText.split('{');
  for (let i = 0; i < parts.length - 1; i++) {
    const sel = parts[i].split('}').pop();
    const selectors = sel.split(',').map(s => s.trim());
    selectors.forEach(s => {
      let m;
      const classRe = /\.([-_a-zA-Z0-9]+)/g;
      while ((m = classRe.exec(s))) classSet.add(m[1]);
      const idRe = /#([-_a-zA-Z0-9]+)/g;
      while ((m = idRe.exec(s))) idSet.add(m[1]);
    });
  }
  return { classSet, idSet };
}

function extractUsedFromText(text) {
  const used = new Set();
  // class="..." and class='...'
  const classAttrRe = /class(Name)?\s*=\s*["']([^"']+)["']/g;
  let m;
  while ((m = classAttrRe.exec(text))) {
    m[2].split(/\s+/).filter(Boolean).forEach(c => used.add(c.replace(/[^-_.a-zA-Z0-9]/g, '')));
  }
  // classList.add('a','b') or .add("a")
  const classListRe = /classList\.add\(([^)]+)\)/g;
  while ((m = classListRe.exec(text))) {
    const items = m[1].split(',').map(s => s.replace(/["'\s]/g, ''));
    items.forEach(it => it && used.add(it));
  }
  // querySelector('.class') or querySelectorAll
  const qsRe = /querySelector(All)?\s*\([^)]*?["'`]([#.][-_a-zA-Z0-9]+)["'`][^)]*\)/g;
  while ((m = qsRe.exec(text))) {
    const token = m[2];
    if (token.startsWith('.')) used.add(token.slice(1));
    if (token.startsWith('#')) used.add(token.slice(1));
  }
  return used;
}

function main() {
  if (!fs.existsSync(CSS_PATH)) {
    console.error('style.css not found at', CSS_PATH);
    process.exit(1);
  }
  const cssText = fs.readFileSync(CSS_PATH, 'utf8');
  const { classSet, idSet } = parseCssSelectors(cssText);

  const files = readFiles(ROOT, ['.html', '.js', '.py', '.md']);
  const used = new Set();
  for (const f of files) {
    try {
      const txt = fs.readFileSync(f, 'utf8');
      const found = extractUsedFromText(txt);
      found.forEach(x => used.add(x));
    } catch (e) {
      // ignore
    }
  }

  const cssClasses = Array.from(classSet).sort();
  const cssIds = Array.from(idSet).sort();

  const usedClasses = new Set();
  cssClasses.forEach(c => { if (used.has(c)) usedClasses.add(c); });

  const unused = cssClasses.filter(c => !usedClasses.has(c));

  const report = {
    scannedFiles: files.length,
    cssClassesCount: cssClasses.length,
    cssIdsCount: cssIds.length,
    usedClasses: Array.from(usedClasses).sort(),
    unusedClasses: unused,
    cssClassesAll: cssClasses,
    cssIdsAll: cssIds
  };

  const outPath = path.join(ROOT, 'scripts', 'unused-css-report.json');
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2), 'utf8');
  console.log('Wrote report to', outPath);
  console.log('CSS classes found:', cssClasses.length, 'unused candidates:', unused.length);
}

main();
