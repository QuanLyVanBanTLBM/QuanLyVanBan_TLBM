---
name: design-tokens-compliance
description: Enforce CSS design tokens compliance from frontend/src/styles/global.css. Use when writing, modifying, or reviewing CSS files, styled components, or inline styles in frontend/src.
---

# Design Tokens Compliance

Enforce that all CSS styling uses the project's centralized design tokens defined in `frontend/src/styles/global.css`, prohibiting arbitrary hex color codes and hardcoded pixel sizes.

## Core Rules

### 1. Color System (Strict Token Usage)
- Never use raw hex (`#2563eb`), rgb/rgba, or hsl values in feature CSS files.
- Always reference the designated CSS custom property:
  - **Brand Colors**: `var(--color-primary)`, `var(--color-primary-hover)`, `var(--color-primary-light)`, `var(--color-secondary)`, `var(--color-secondary-hover)`
  - **Semantic Feedback**:
    - Success: `var(--color-success)`, `var(--color-success-bg)`
    - Warning: `var(--color-warning)`, `var(--color-warning-bg)`
    - Danger/Error: `var(--color-danger)`, `var(--color-danger-bg)`
    - Info: `var(--color-info)`, `var(--color-info-bg)`
  - **Surfaces & Borders**:
    - `var(--color-surface-white)`
    - `var(--color-border-subtle)` (Slate 200)
    - `var(--color-border-medium)` (Slate 300)
    - `var(--color-border-strong)` (Slate 400)

### 2. Typography Scale
- Never use arbitrary `font-size: 14px`, `font-size: 18px` etc.
- Use the official typography scale:
  - `var(--font-2xs)`: 0.625rem (10px) - Micro badges, auxiliary metadata
  - `var(--font-xs)`: 0.75rem (12px) - Captions, timestamps, small tags
  - `var(--font-sm)`: 0.875rem (14px) - Secondary text, data tables, menus
  - `var(--font-base)`: 1.000rem (16px) - Body text, form inputs
  - `var(--font-md)`: 1.125rem (18px) - Card titles, highlighted sections
  - `var(--font-lg)`: 1.250rem (20px) - Section group headers
  - `var(--font-xl)`: 1.500rem (24px) - Module titles, modal headers
  - `var(--font-2xl)`: 1.875rem (30px) - Page titles
  - `var(--font-3xl)`: 2.250rem (36px) - Stats metrics, hero banners

### 3. Spacing & Border Radius
- **Spacing**: `var(--space-1)` (4px), `var(--space-2)` (8px), `var(--space-3)` (12px), `var(--space-4)` (16px), `var(--space-6)` (24px), `var(--space-8)` (32px).
- **Radius**: `var(--radius-sm)` (8px), `var(--radius-md)` (12px), `var(--radius-lg)` (16px), `var(--radius-full)` (9999px).

### 4. Verification Checklist (Run before completing task)
- [ ] No hex color codes (`#[0-9a-fA-F]{3,8}`) in feature CSS files.
- [ ] No raw `font-size: ...px` declarations.
- [ ] All margins and paddings utilize `var(--space-*)`.
- [ ] Layout remains visually coherent across themes (Dark, Light, Gray-Black).
