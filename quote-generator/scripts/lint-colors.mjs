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

if (violations.length > 0) {
  console.error('Color lint failed. Resolve color through the brand palette and theme color scope.');
  for (const violation of violations) {
    console.error(`- ${violation.relativePath}:${violation.line} -> ${violation.label} \`${violation.token}\``);
  }
  process.exitCode = 1;
} else {
  console.log('Color lint passed.');
}
