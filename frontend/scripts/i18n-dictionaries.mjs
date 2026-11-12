// Đọc từ điển theo module tại src/i18n/<module>/{vi,en}.json (cùng tập file mà translate.ts ghép qua import.meta.glob).
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const LANGUAGES = ['vi', 'en'];
export const i18nDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'src', 'i18n');

const readJson = (file) => JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));

/** Danh sách module: mỗi thư mục con của src/i18n, kèm đường dẫn file của từng ngôn ngữ (null nếu thiếu). */
export function listModules() {
  return readdirSync(i18nDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => {
      const files = {};
      for (const lang of LANGUAGES) {
        const file = path.join(i18nDir, entry.name, `${lang}.json`);
        files[lang] = existsSync(file) ? file : null;
      }
      return { name: entry.name, files };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** Làm phẳng thành Map<"a.b.c", giá trị lá>. */
export function flatten(value, prefix = '', result = new Map()) {
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
    for (const [key, child] of Object.entries(value)) flatten(child, prefix ? `${prefix}.${key}` : key, result);
  } else {
    result.set(prefix, value);
  }
  return result;
}

/** Ghép đệ quy từ điển các module của một ngôn ngữ, giống translate.ts. */
export function loadDictionary(lang) {
  const merge = (target, source) => {
    for (const [key, value] of Object.entries(source)) {
      const current = target[key];
      if (value && typeof value === 'object' && current && typeof current === 'object') merge(current, value);
      else target[key] = value && typeof value === 'object' ? merge({}, value) : value;
    }
    return target;
  };
  return listModules()
    .filter((module) => module.files[lang])
    .reduce((dict, module) => merge(dict, readJson(module.files[lang])), {});
}

export { readJson };
