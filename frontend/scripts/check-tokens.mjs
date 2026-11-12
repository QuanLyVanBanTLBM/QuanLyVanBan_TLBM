import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const checkedTargets = [
  path.join(frontendDir, 'src', 'components', 'records'),
  path.join(frontendDir, 'src', 'pages', 'records'),
  path.join(frontendDir, 'src', 'lib', 'recordsService.ts'),
  path.join(frontendDir, 'src', 'types', 'records.ts'),
];

async function collectFiles(target) {
  const entries = await readdir(target, { withFileTypes: true }).catch(() => null);
  if (!entries) return [target];

  const files = [];
  for (const entry of entries) {
    const child = path.join(target, entry.name);
    if (entry.isDirectory()) files.push(...(await collectFiles(child)));
    else if (/\.(css|js|jsx|ts|tsx)$/.test(entry.name)) files.push(child);
  }
  return files;
}

const rawColor = /#[0-9A-Fa-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\s*\(/;
const arbitraryColor = /(?:bg|text|border|ring|fill|stroke)-\[(?:#|rgb|rgba|hsl|hsla)/;
const paletteColor = /(?:bg|text|border|ring|fill|stroke)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/;
const errors = [];

for (const target of checkedTargets) {
  for (const file of await collectFiles(target)) {
    const lines = (await readFile(file, 'utf8')).split(/\r?\n/);
    lines.forEach((line, index) => {
      if (rawColor.test(line) || arbitraryColor.test(line) || paletteColor.test(line)) {
        errors.push(`${path.relative(frontendDir, file)}:${index + 1}: ${line.trim()}`);
      }
    });
  }
}

if (errors.length > 0) {
  console.error('Design-token check failed. Use semantic tokens instead of raw or palette colors:');
  errors.forEach((error) => console.error(`- ${error}`));
  process.exit(1);
}

console.log('Design-token check passed for the complete Records module.');
