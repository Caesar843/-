# Theme Switch (Light/Dark)

## Overview
- Strategy: CSS design tokens + `html[data-theme="dark"]` switch.
- Source of truth: `static/css/tokens.css` (light + dark).
- Runtime toggle: `static/js/theme.js` with localStorage persistence.
- Early theme apply: inline script in `templates/base.html` `<head>` to avoid FOUC.

## Tokens (semantic)
- Background/surfaces: `--bg`, `--surface`, `--surface-2`, `--overlay`
- Text: `--text`, `--text-muted`, `--text-inverse`
- Borders/dividers: `--border`, `--divider`
- Brand/status: `--primary`, `--primary-hover`, `--success`, `--warning`, `--danger`, `--info`
- Interaction: `--focus-ring`, `--shadow`, `--shadow-strong`
- Table: `--table-header`, `--table-row-hover`, `--table-stripe`
- Form: `--input-bg`, `--input-text`, `--input-placeholder`, `--input-border`, `--input-focus`, `--input-invalid`

## Files touched
- `static/css/tokens.css` (new)
- `static/js/theme.js` (new)
- `static/css/ui-tokens.css` (map ops tokens to semantic tokens)
- `static/css/ui-components.css` (replace hardcoded colors with tokens)
- `templates/base.html` (load tokens, inject early theme, toggle button, global dark styles)

## Toggle logic
1. If `localStorage.theme` is `light` or `dark`, use it.
2. Else follow `prefers-color-scheme`.
3. Toggle button switches `light` <-> `dark` and persists to localStorage.

## Rollback
1. Remove `static/css/tokens.css` and `static/js/theme.js`.
2. Remove the `<link rel="stylesheet" href="{% static 'css/tokens.css' %}">` and theme bootstrap script in `templates/base.html`.
3. Remove the theme toggle button in `templates/base.html`.
4. Revert `static/css/ui-tokens.css`, `static/css/ui-components.css`, and related theme styles in `templates/base.html`.

## Self-check list
- Theme toggles and persists after reload.
- Login/register: inputs, errors, and icons readable in dark.
- Lists/tables: header/hover/stripe readable in dark.
- Modal/overlay: backdrop and content readable in dark.
- Admin/non-admin behavior unchanged.
- No visible flash on first render.
