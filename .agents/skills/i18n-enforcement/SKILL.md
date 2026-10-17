---
name: i18n-enforcement
description: Enforce internationalization (i18n) standards for React components and translation dictionaries. Use when creating, editing, or reviewing React JSX files, forms, modals, error messages, and UI text in frontend/src.
---

# i18n Enforcement (Bilingual Quality Gate)

Enforce that all user-facing UI text uses the project's centralized translation system, preventing hardcoded text and ensuring bilingual synchronization between Vietnamese and English.

## Core Rules

### 1. Zero Raw Text in JSX
- Never hardcode display text directly in JSX elements:
  - **Bad**: `<h1>Danh sách sinh nhật</h1>`, `<button>Lưu lại</button>`, `placeholder="Nhập họ tên..."`
  - **Good**: `<h1>{t('birthday.title')}</h1>`, `<button>{t('common.save')}</button>`, `placeholder={t('common.searchPlaceholder')}`
- Always import and call `useTranslation` hook from `frontend/src/hooks/useTranslation`:
  ```jsx
  import { useTranslation } from '../hooks/useTranslation';

  export default function MyComponent() {
    const { t, language, changeLanguage } = useTranslation();
    return <div>{t('namespace.key')}</div>;
  }
  ```
- For parameterized strings, use interpolation:
  ```jsx
  <p>{t('birthday.turningAge', { age: 28, name: staff.name })}</p>
  ```

### 2. Mandatory Bilingual Synchronization
- All translation keys must exist in **both** `vi` (Vietnamese) and `en` (English) trees inside `frontend/src/i18n/translations.js`.
- Never add a key to `vi` without adding the corresponding `en` entry (and vice versa).
- Follow the established namespace hierarchy:
  - `common`: Generic actions (`save`, `cancel`, `confirm`, `delete`, `loading`, `error`...)
  - `nav`: Sidebar & header navigation labels
  - `dashboard`: Dashboard-specific widgets and summaries
  - `birthday`: Birthday module 7.2 components
  - `documents`: Document management features

### 3. Verification Checklist (Run before completing task)
- [ ] No hardcoded Vietnamese or English strings remain in `.jsx` files.
- [ ] Every `t('a.b')` call has a matching entry in `frontend/src/i18n/translations.js`.
- [ ] Both `translations.vi` and `translations.en` contain the new key with correct meaning.
- [ ] Dynamic parameters `{param}` in template strings match the arguments passed to `t()`.
