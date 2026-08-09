import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const projectRoot = process.cwd();
const targetDirectories = ['components/display', 'app'];

const bannedPatterns = [
  {
    label: 'brand context in display system',
    pattern: /\buseBrand\s*\(/g,
  },
  {
    label: 'raw brand data in display system',
    pattern: /\bBRANDS_DATA\b/g,
  },
  {
    label: 'legacy visibility class',
    pattern: /\bno-print\b|\bno-screen\b/g,
  },
];

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        return collectFiles(fullPath);
      }
      return fullPath.endsWith('.tsx') ? [fullPath] : [];
    })
  );

  return nested.flat();
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
    const relativePath = path.relative(projectRoot, filePath);
    const source = await readFile(filePath, 'utf8');

    for (const { label, pattern } of bannedPatterns) {
      pattern.lastIndex = 0;
      let match;
      while ((match = pattern.exec(source)) !== null) {
        const allowedDisplayPageContext =
          relativePath === 'app/error.tsx' && match[0].includes('no-');
        if (allowedDisplayPageContext) {
          continue;
        }

        violations.push({
          filePath: relativePath,
          line: getLineNumber(source, match.index),
          label,
          token: match[0],
        });
      }
    }
  }

  if (violations.length === 0) {
    console.log('Display system lint passed.');
    return;
  }

  console.error(
    'Display system lint failed. Public display code must consume theme/view-model contracts instead of raw brand/runtime shortcuts.'
  );
  for (const violation of violations) {
    console.error(
      `- ${violation.filePath}:${violation.line} -> ${violation.label} \`${violation.token}\``
    );
  }
  process.exitCode = 1;
}

await main();
