/**
 * Synchronize static legacy files (published/ and assets/) from monorepo root
 * to quote-generator/public/ directory so Next.js serves them directly.
 */

const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const PUBLIC_DIR = path.resolve(__dirname, '..', 'public');

const SOURCE_PUBLISHED = path.join(PROJECT_ROOT, 'published');
const TARGET_PUBLISHED = path.join(PUBLIC_DIR, 'published');

const SOURCE_ASSETS = path.join(PROJECT_ROOT, 'assets');
const TARGET_ASSETS = path.join(PUBLIC_DIR, 'assets');

function copyRecursiveSync(src, dest) {
  if (!fs.existsSync(src)) {
    return;
  }
  const stats = fs.statSync(src);
  if (stats.isDirectory()) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }
    const entries = fs.readdirSync(src);
    for (const entry of entries) {
      if (entry === '.git' || entry === 'node_modules' || entry === '.DS_Store') {
        continue;
      }
      copyRecursiveSync(path.join(src, entry), path.join(dest, entry));
    }
  } else {
    let shouldCopy = true;
    if (fs.existsSync(dest)) {
      const destStats = fs.statSync(dest);
      if (destStats.size === stats.size && destStats.mtimeMs >= stats.mtimeMs) {
        shouldCopy = false;
      }
    }
    if (shouldCopy) {
      const destDir = path.dirname(dest);
      if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
      }
      fs.copyFileSync(src, dest);
    }
  }
}

function main() {
  console.log('[sync-legacy-assets] Synchronizing static assets to quote-generator/public...');

  if (fs.existsSync(SOURCE_PUBLISHED)) {
    console.log(`[sync-legacy-assets] Copying ${SOURCE_PUBLISHED} -> ${TARGET_PUBLISHED}`);
    copyRecursiveSync(SOURCE_PUBLISHED, TARGET_PUBLISHED);
  } else {
    console.warn(`[sync-legacy-assets] Source published directory not found at ${SOURCE_PUBLISHED}`);
  }

  if (fs.existsSync(SOURCE_ASSETS)) {
    console.log(`[sync-legacy-assets] Copying ${SOURCE_ASSETS} -> ${TARGET_ASSETS}`);
    copyRecursiveSync(SOURCE_ASSETS, TARGET_ASSETS);
  } else {
    console.warn(`[sync-legacy-assets] Source assets directory not found at ${SOURCE_ASSETS}`);
  }

  console.log('[sync-legacy-assets] Sync completed successfully.');
}

main();
