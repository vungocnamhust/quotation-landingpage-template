import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const projectRoot = process.cwd();
const targetDirectories = ['app', 'components/display', 'display', 'config'];
// Palette fixtures and production profile resolver are the only code allowed to
// construct CSS color values. Renderers consume their resolved scopes only.
const allowedFiles = new Set(['config/themeTokens.ts', 'config/runtimeThemeTokens.ts']);
const bannedPatterns = [
  { label: 'literal hex color', pattern: /#[0-9a-fA-F]{3,8}\b/g },
  { label: 'literal rgba color', pattern: /rgba?\(/g },
  { label: 'legacy color variable', pattern: /var\(--(?:surface|text|accent|border|map|display-line|shadow-custom)/g },
  { label: 'literal component color prop', pattern: /\b(?:color|background|backgroundColor)\s*=\s*["'](?:#|rgb)/g },
];

async function collectFiles(directory) {
  const entries = await readdir(path.join(projectRoot, directory), { withFileTypes: true });
  const nested = await Promise.all(entries.map(async (entry) => {
    const fullPath = path.join(projectRoot, directory, entry.name);
    if (entry.isDirectory()) return collectFiles(path.join(directory, entry.name));
    return /\.(?:ts|tsx|css)$/.test(entry.name) ? [fullPath] : [];
  }));
  return nested.flat();
}

function lineNumber(source, index) {
  return source.slice(0, index).split('\n').length;
}

const files = (await Promise.all(targetDirectories.map(collectFiles))).flat();
const violations = [];

for (const filePath of files) {
  const relativePath = path.relative(projectRoot, filePath);
  if (allowedFiles.has(relativePath)) continue;
  const source = await readFile(filePath, 'utf8');

  for (const { label, pattern } of bannedPatterns) {
    pattern.lastIndex = 0;
    let match;
    while ((match = pattern.exec(source)) !== null) {
      violations.push({ relativePath, label, token: match[0], line: lineNumber(source, match.index) });
    }
  }
}

function parseHex(hex) {
  return {
    r: Number.parseInt(hex.slice(1, 3), 16),
    g: Number.parseInt(hex.slice(3, 5), 16),
    b: Number.parseInt(hex.slice(5, 7), 16),
  };
}

function relativeLuminance(hex) {
  const { r, g, b } = parseHex(hex);
  const channels = [r, g, b].map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.03928 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function getContrastRatio(foreground, background) {
  const lighter = Math.max(relativeLuminance(foreground), relativeLuminance(background));
  const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

// Deterministic WCAG 2.1 AA validation on brand palettes
const brandsDataSource = await readFile(path.join(projectRoot, 'data/brandsData.ts'), 'utf8');
const brandPaletteRegex = /id:\s*'([^']+)'[\s\S]*?palette:\s*\{([^}]+)\}/g;
let brandMatch;

while ((brandMatch = brandPaletteRegex.exec(brandsDataSource)) !== null) {
  const brandId = brandMatch[1];
  const paletteBlock = brandMatch[2];
  const colorMatches = [...paletteBlock.matchAll(/(\w+):\s*'([^']+)'/g)];
  const palette = Object.fromEntries(colorMatches.map((m) => [m[1], m[2]]));

  const checks = [
    { label: 'ink on canvas (normal text >= 4.5)', fg: palette.ink, bg: palette.canvas, min: 4.5 },
    { label: 'mutedInk on canvas (normal text >= 4.5)', fg: palette.mutedInk, bg: palette.canvas, min: 4.5 },
    { label: 'onContrast on contrast (contrast text >= 4.5)', fg: palette.onContrast, bg: palette.contrast, min: 4.5 },
    { label: 'onContrast on storyContrast (story text >= 4.5)', fg: palette.onContrast, bg: palette.storyContrast, min: 4.5 },
    { label: 'investmentText on investmentSurface (investment text >= 4.5)', fg: palette.investmentText, bg: palette.investmentSurface, min: 4.5 },
    { label: 'focus on canvas (focus ring >= 3.0)', fg: palette.focus, bg: palette.canvas, min: 3.0 },
  ];

  for (const { label, fg, bg, min } of checks) {
    if (!fg || !bg) continue;
    const ratio = getContrastRatio(fg, bg);
    if (ratio < min) {
      violations.push({
        relativePath: 'data/brandsData.ts',
        label: `WCAG 2.1 AA violation for brand "${brandId}": ${label} (${ratio.toFixed(2)}:1 < ${min}:1)`,
        token: `${fg} on ${bg}`,
        line: 1,
      });
    }
  }

  const actionContrast = Math.max(
    getContrastRatio(palette.ink, palette.accent),
    getContrastRatio(palette.onContrast, palette.accent)
  );
  if (actionContrast < 4.5) {
    violations.push({
      relativePath: 'data/brandsData.ts',
      label: `WCAG 2.1 AA violation for brand "${brandId}": primary action contrast (${actionContrast.toFixed(2)}:1 < 4.5:1)`,
      token: palette.accent,
      line: 1,
    });
  }
}

if (violations.length > 0) {
  console.error('Color lint failed. Resolve color through the brand palette and theme color scope.');
  for (const violation of violations) {
    console.error(`- ${violation.relativePath}:${violation.line} -> ${violation.label} \`${violation.token}\``);
  }
  process.exitCode = 1;
} else {
  console.log('Color lint passed (Static tokens & WCAG 2.1 AA verified).');
}
