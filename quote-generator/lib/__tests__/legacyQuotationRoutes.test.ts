import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('legacyQuotationRoutes static file contracts', () => {
  const publicDir = path.resolve(__dirname, '..', '..', 'public');
  const publishedDir = path.join(publicDir, 'published');
  const assetsDir = path.join(publicDir, 'assets');

  it('verifies that quo_f7175e110605ab exists in public/published', () => {
    const quoDir = path.join(publishedDir, 'quo_f7175e110605ab');
    assert.ok(fs.existsSync(quoDir), 'quo_f7175e110605ab directory must exist');
    assert.ok(fs.existsSync(path.join(quoDir, 'ctx.json')), 'ctx.json must exist');
    assert.ok(fs.existsSync(path.join(quoDir, 'v131.html')), 'v131.html must exist');
    assert.ok(fs.existsSync(path.join(quoDir, 'pdf.html')), 'pdf.html must exist');
  });

  it('scans and finds latest version for quo_f7175e110605ab', () => {
    const quoDir = path.join(publishedDir, 'quo_f7175e110605ab');
    const files = fs.readdirSync(quoDir);
    const versions = files
      .map((f) => {
        const m = f.match(/^v(\d+)(?:_[a-z]{2})?\.html$/i);
        return m ? parseInt(m[1], 10) : 0;
      })
      .filter((v) => v > 0);

    const maxVersion = Math.max(...versions);
    assert.equal(maxVersion, 131, 'Expected latest version 131');
  });

  it('verifies destination images exist in public/assets', () => {
    const hanoiHero = path.join(assetsDir, 'ha-noi', 'hero', 'hero4.jpg');
    assert.ok(fs.existsSync(hanoiHero), 'Hanoi hero image must exist');

    const safarLogo = path.join(assetsDir, 'vietnam-safar-logo.png');
    assert.ok(fs.existsSync(safarLogo), 'Vietnam Safar logo must exist');
  });
});
