import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const projectRoot = process.cwd();
const targetDirectories = ['app', 'components'];

const bannedPatterns = [
  {
    label: 'legacy font role class',
    pattern: /\bfont-(heading|body|accent)\b/g,
  },
  {
    label: 'font weight utility',
    pattern: /\bfont-(thin|extralight|light|normal|medium|semibold|bold|extrabold|black)\b/g,
  },
  {
    label: 'text size utility',
    pattern: /\btext-(xs|sm|base|lg|xl|[2-9]xl)\b|\btext-\[(?:\d+(?:\.\d+)?)(?:px|rem|em)\]/g,
  },
  {
    label: 'line-height utility',
    pattern: /\bleading-(none|tight|snug|normal|relaxed|loose|\[[^\]]+\])\b/g,
  },
  {
    label: 'tracking utility',
    pattern: /\btracking-(tighter|tight|normal|wide|wider|widest|\[[^\]]+\])\b/g,
  },
  {
    label: 'uppercase utility',
    pattern: /\buppercase\b/g,
  },
  {
    label: 'italic utility',
    pattern: /\bitalic\b/g,
  },
];

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        return collectFiles(fullPath);
      }
      return fullPath.endsWith('.tsx') || fullPath.endsWith('.css') ? [fullPath] : [];
    })
  );

  return files.flat();
}

function getLineNumber(source, matchIndex) {
  return source.slice(0, matchIndex).split('\n').length;
}

async function main() {
  const files = (
    await Promise.all(
      targetDirectories.map((directory) => collectFiles(path.join(projectRoot, directory)))
    )
  ).flat();

  const violations = [];

  for (const filePath of files) {
    const source = await readFile(filePath, 'utf8');

    for (const { label, pattern } of bannedPatterns) {
      pattern.lastIndex = 0;
      let match;
      while ((match = pattern.exec(source)) !== null) {
        violations.push({
          filePath,
          line: getLineNumber(source, match.index),
          label,
          token: match[0],
        });
      }
    }

    if (filePath.endsWith('.css')) {
      const cssTypographyPattern = /(^|[\s{;])(font-size|font-weight|font-style|font\s*:|line-height|letter-spacing|text-transform)\s*:/g;
      let match;
      while ((match = cssTypographyPattern.exec(source)) !== null) {
        violations.push({
          filePath,
          line: getLineNumber(source, match.index),
          label: 'CSS content typography declaration',
          token: match[2],
        });
      }
    }
  }

  if (violations.length === 0) {
    console.log('Typography lint passed.');
    return;
  }

  console.error('Typography lint failed. Use semantic `typo-*` classes instead of raw typography utilities.');
  for (const violation of violations) {
    const relativePath = path.relative(projectRoot, violation.filePath);
    console.error(
      `- ${relativePath}:${violation.line} -> ${violation.label} \`${violation.token}\``
    );
  }
  process.exitCode = 1;
}

await main();
