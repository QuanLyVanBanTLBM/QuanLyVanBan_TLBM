// Kiểm tra file CSS trong src/ (trừ styles/global.css, nơi định nghĩa token) không dùng
// mã màu hex và font-size đơn vị px. Chỉ quét giá trị khai báo trong file .css.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const srcDir = join(root, 'src');
const tokenFile = join(srcDir, 'styles', 'global.css');

const HEX = /#[0-9a-fA-F]{3,8}\b/;
const FONT_PX = /\d+(\.\d+)?px/;

const cssFiles = readdirSync(srcDir, { recursive: true })
  .map((file) => join(srcDir, file))
  .filter((file) => file.endsWith('.css') && file !== tokenFile);

const violations = [];

for (const file of cssFiles) {
  // Thay comment bằng khoảng trắng cùng độ dài để giữ đúng số dòng.
  const css = readFileSync(file, 'utf8').replace(/\/\*[\s\S]*?\*\//g, (c) => c.replace(/[^\n]/g, ' '));
  for (const match of css.matchAll(/([\w-]+)\s*:\s*([^;{}]+)/g)) {
    const [, property, value] = match;
    const isFont = property === 'font-size' || property === 'font';
    // Bỏ url(...) để không nhầm tham chiếu fragment như url(#abc) với mã màu.
    const reason = HEX.test(value.replace(/url\([^)]*\)/g, '')) ? 'mã màu hex' : isFont && FONT_PX.test(value) ? 'font-size px' : null;
    if (!reason) continue;
    const line = css.slice(0, match.index).split('\n').length;
    const path = relative(root, file).split(sep).join('/');
    violations.push(`${path}:${line} ${reason}: ${property}: ${value.trim()}`);
  }
}

if (violations.length) {
  for (const v of violations) console.error(v);
  console.error(`Vi phạm design token: ${violations.length}. Dùng var(--color-...) / var(--font-...) từ src/styles/global.css.`);
  process.exit(1);
}

console.log(`Design token OK: ${cssFiles.length} file CSS.`);
