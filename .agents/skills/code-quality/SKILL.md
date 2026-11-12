---
name: code-quality
description: Run full-stack code quality and build verification gates (Django system check/tests, Vite frontend build, i18n and CSS tokens compliance). Use before completing any task, preparing a commit, or reviewing code.
---

# Full-Stack Code Quality Gate

Execute automated checks and manual verification across both Backend (Django) and Frontend (React/Vite).

## Instructions

### 1. Automated Checks

#### Frontend Verification (Definition of Done Gate):
```bash
# 1. Compile & Build check with Vite (MUST PASS with zero errors)
pnpm --dir frontend run build

# If pnpm is not in path, use:
# npm --prefix frontend run build
```

#### Backend Verification (Django Gate):
```bash
# 2. Django System Check (verify models, URLs, settings)
python backend/manage.py check

# 3. Run Backend Test Suite
python backend/manage.py test
```

### 2. Static Compliance Checks

- **i18n Compliance**:
  - Scan modified `.jsx` files: Ensure NO raw user-facing text exists without `t('namespace.key')`.
  - Verify `frontend/src/i18n/translations.js`: Ensure new keys exist in **both** `vi` and `en`.
- **CSS Design Tokens Compliance**:
  - Scan modified `.css` files: Ensure NO raw hex color codes (`#...`) or raw pixel font sizes (`font-size: ..px`).
  - All colors and typography must use `var(--color-...)` and `var(--font-...)`.

### 3. Manual Review Checklist

- [ ] **Frontend**:
  - [ ] No raw strings hardcoded in JSX.
  - [ ] Translations added to both `vi` and `en`.
  - [ ] Design tokens used in all stylesheets.
  - [ ] Vite build completes with zero errors (`pnpm --dir frontend run build`).
- [ ] **Backend**:
  - [ ] N+1 queries avoided (`select_related` for ForeignKey, `prefetch_related` for M2M).
  - [ ] Proper error handling (no empty `except: pass`).
  - [ ] Form and model validation encapsulated correctly.
  - [ ] Django system check passes (`python backend/manage.py check`).

### 4. Report Findings

Organize issues by severity:
- **Critical (must fix)**: Build failure, syntax error, missing translation key, runtime exception, N+1 query.
- **Warning (should fix)**: Token violation, unused imports, inconsistent naming.
- **Suggestion (could improve)**: Code formatting, minor optimization.
