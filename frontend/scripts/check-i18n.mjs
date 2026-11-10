// Kiểm tra từ điển theo module tại src/i18n/<module>/{vi,en}.json:
// - mỗi module có đủ vi.json và en.json, hai file cùng tập key (so theo đường dẫn key đã làm phẳng);
// - không có key (hoặc tiền tố key) khai báo ở hai module, vì từ điển chạy thực tế là phép ghép các module.
import path from 'node:path';
import { LANGUAGES, flatten, i18nDir, listModules, readJson } from './i18n-dictionaries.mjs';

const errors = [];
const rel = (file) => path.relative(path.dirname(i18nDir), file).split(path.sep).join('/');
const owners = Object.fromEntries(LANGUAGES.map((lang) => [lang, new Map()]));
let total = 0;

for (const module of listModules()) {
  const keys = {};
  for (const lang of LANGUAGES) {
    const file = module.files[lang];
    if (!file) {
      errors.push(`Thiếu file i18n/${module.name}/${lang}.json`);
      continue;
    }
    keys[lang] = flatten(readJson(file));
    for (const key of keys[lang].keys()) {
      const other = owners[lang].get(key);
      if (other) errors.push(`Key ${key} khai báo ở cả ${rel(other)} và ${rel(file)}`);
      else owners[lang].set(key, file);
    }
  }
  if (!keys.vi || !keys.en) continue;
  for (const key of keys.vi.keys()) if (!keys.en.has(key)) errors.push(`Thiếu trong ${rel(module.files.en)}: ${key}`);
  for (const key of keys.en.keys()) if (!keys.vi.has(key)) errors.push(`Thiếu trong ${rel(module.files.vi)}: ${key}`);
  total += keys.vi.size;
}

// Một key lá không được đồng thời là tiền tố của key khác (ví dụ "a.b" là chuỗi ở module này, "a.b.c" ở module khác).
for (const lang of LANGUAGES) {
  const keys = owners[lang];
  for (const [key, file] of keys) {
    const parts = key.split('.');
    for (let i = 1; i < parts.length; i += 1) {
      const prefix = parts.slice(0, i).join('.');
      if (keys.has(prefix)) errors.push(`Key ${prefix} là chuỗi ở ${rel(keys.get(prefix))} nhưng có key con ở ${rel(file)}`);
    }
  }
}

const uniqueErrors = [...new Set(errors)];
if (uniqueErrors.length) {
  for (const error of uniqueErrors) console.error(error);
  console.error(`i18n lệch: ${uniqueErrors.length} lỗi.`);
  process.exit(1);
}

console.log(`i18n khớp: ${total} key trong ${listModules().length} module.`);
