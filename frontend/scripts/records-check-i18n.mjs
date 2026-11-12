import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadDictionary } from './i18n-dictionaries.mjs';

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const recordsSources = [
  path.join(frontendDir, 'src', 'components', 'records'),
  path.join(frontendDir, 'src', 'pages', 'records'),
];

function flatten(value, prefix = '', result = new Map()) {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' || value === null) {
    result.set(prefix, value);
    return result;
  }

  if (typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`Translation key "${prefix}" has an unsupported value.`);
  }

  for (const [key, child] of Object.entries(value)) {
    flatten(child, prefix ? `${prefix}.${key}` : key, result);
  }
  return result;
}

function placeholders(value) {
  if (typeof value !== 'string') return [];
  return [...value.matchAll(/\{([A-Za-z0-9_]+)\}/g)]
    .map((match) => match[1])
    .sort();
}

async function sourceFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await sourceFiles(target)));
    else if (/\.(ts|tsx)$/.test(entry.name) && !/\.test\.(ts|tsx)$/.test(entry.name)) files.push(target);
  }
  return files;
}

const [vi, en] = [loadDictionary('vi'), loadDictionary('en')];
const viKeys = flatten(vi);
const enKeys = flatten(en);
const errors = [];

for (const key of viKeys.keys()) {
  if (!enKeys.has(key)) errors.push(`Missing English key: ${key}`);
}
for (const key of enKeys.keys()) {
  if (!viKeys.has(key)) errors.push(`Missing Vietnamese key: ${key}`);
}
for (const key of viKeys.keys()) {
  if (!enKeys.has(key)) continue;
  if (typeof viKeys.get(key) !== typeof enKeys.get(key)) {
    errors.push(
      `Value type mismatch at ${key}: vi=${typeof viKeys.get(key)}, en=${typeof enKeys.get(key)}`
    );
    continue;
  }
  const viPlaceholders = placeholders(viKeys.get(key));
  const enPlaceholders = placeholders(enKeys.get(key));
  if (viPlaceholders.join('|') !== enPlaceholders.join('|')) {
    errors.push(
      `Placeholder mismatch at ${key}: vi=[${viPlaceholders.join(', ')}], en=[${enPlaceholders.join(', ')}]`
    );
  }
}

const vietnameseText = /[À-ỹ]/u;
for (const directory of recordsSources) {
  for (const file of await sourceFiles(directory)) {
    const lines = (await readFile(file, 'utf8')).split(/\r?\n/);
    lines.forEach((line, index) => {
      if (vietnameseText.test(line)) {
        errors.push(
          `Hardcoded Vietnamese text in ${path.relative(frontendDir, file)}:${index + 1}`
        );
      }
    });
  }
}

if (errors.length > 0) {
  console.error('i18n check failed:');
  errors.forEach((error) => console.error(`- ${error}`));
  process.exit(1);
}

console.log(
  `i18n check passed: ${viKeys.size} keys are aligned and Records UI has no hardcoded Vietnamese text.`
);
