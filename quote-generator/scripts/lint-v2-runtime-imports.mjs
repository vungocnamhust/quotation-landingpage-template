import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, extname, join, resolve } from 'node:path';

const projectRoot = process.cwd();
const runtimeRoots = [
  'app/[locale]',
  'app/layout.tsx',
  'app/content-studio',
  'app/quotations',
  'app/internal',
  'app/media',
  'components/DisplayPage.tsx',
  'components/quotation-workspace',
  'display/runtimePageBuilder.ts',
  'display/pageBuilder.ts',
  'config/runtimeThemeTokens.ts',
  'lib/publicQuotationApi.ts',
];
const sourceExtensions = ['.ts', '.tsx'];
const visited = new Set();
const offenders = new Set();

function sourceFiles(path) {
  const stat = statSync(path);
  if (!stat.isDirectory()) return sourceExtensions.includes(extname(path)) ? [path] : [];
  return readdirSync(path).flatMap((entry) => sourceFiles(join(path, entry)));
}

function resolveLocalImport(fromFile, specifier) {
  if (!specifier.startsWith('.')) return null;
  const base = resolve(dirname(fromFile), specifier);
  const candidates = [
    ...sourceExtensions.map((extension) => `${base}${extension}`),
    ...sourceExtensions.map((extension) => join(base, `index${extension}`)),
  ];
  return candidates.find(existsSync) ?? null;
}

function inspect(file) {
  if (visited.has(file)) return;
  visited.add(file);
  const source = readFileSync(file, 'utf8');
  // Type-only imports are erased by TypeScript and cannot pull a fixture into
  // an SSR/PDF/client bundle. Runtime imports remain forbidden.
  const runtimeSource = source.replace(/(?:import|export)\s+type\s+[\s\S]*?from\s+['"][^'"]+['"];?/g, '');
  if (runtimeSource.includes('data/brandsData') || runtimeSource.includes('BRANDS_DATA')) {
    offenders.add(file);
    return;
  }
  const importPattern = /(?:import|export)\s+(type\s+)?(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]/g;
  for (const match of source.matchAll(importPattern)) {
    if (match[1]) continue;
    const dependency = resolveLocalImport(file, match[2]);
    if (dependency) inspect(dependency);
  }
}

for (const root of runtimeRoots) {
  for (const file of sourceFiles(join(projectRoot, root))) inspect(file);
}

if (offenders.size) {
  console.error(`V2 runtime reaches static brand fixtures: ${[...offenders].map((file) => file.slice(projectRoot.length + 1)).join(', ')}`);
  process.exit(1);
}
