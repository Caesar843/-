# Dark Mode Readability Fix

## Scan results (white/light backgrounds)
- `static/css/query-dashboard.css`: `.query-list-item` had `background: #f8fafc`, `strong` text `#1d4ed8` (query usage hints).
- `static/css/backup-management.css`: `.backup-form-check` had `background: #f8fafc`; `.backup-info` / `.backup-warning` had light backgrounds with dark-only text colors (backup type cards).
- `templates/base.html`: Bootstrap helpers `.bg-white`, `.bg-light`, `.text-dark` (global light background/text usage).
- `templates/dashboard/index.html`: inline light backgrounds in dashboard cards/icons.
- `templates/partials/modern_theme.html`: light background tokens for info cards and badges.
- `apps/backup/templates/backup/backup_detail.html`, `apps/backup/templates/backup/backup_restore_confirm.html`: `bg-light` and inline `background-color` for panels.
- `templates/finance/finance_list.html`: inline light QR placeholder background.
- `templates/errors/*.html`: inline light backgrounds for error pages.

## Fixes applied (token-driven)
- Added semantic tokens in `static/css/tokens.css`:
  - `--card-bg`, `--card-text`, `--card-muted`
  - `--table-bg`, `--table-head-bg`, `--table-row-hover`
  - `--empty-bg`, `--empty-text`
  - `--radio-card-bg`, `--radio-card-border`, `--radio-card-text`
- Updated `static/css/ui-components.css` to use card/table/empty tokens.
- Updated `static/css/query-dashboard.css` list items to use card tokens (query usage hints).
- Updated `static/css/backup-management.css` radio cards to use radio-card tokens.
- Updated `templates/base.html` global overrides:
  - `.card`, `.bg-white`, `.bg-light`, `.list-group-item`, `.badge.bg-light`, `.table` text
  - All use semantic tokens only.
- Updated error pages to use tokens and high-contrast text:
  - `templates/errors/403.html`, `templates/errors/404.html`, `templates/errors/500.html`

## Remaining candidates (not yet migrated)
- Inline `background-color` in `templates/dashboard/index.html`, `templates/finance/finance_list.html`, `apps/backup/templates/backup/backup_detail.html`, `templates/partials/modern_theme.html`
  - These should be tokenized next to fully eliminate white blocks in dark mode.

## Verification checklist
- Query dashboard usage hints readable in dark mode (no white blocks + pale text).
- Backup create radio cards (full/incremental) readable in dark mode.
- Card, table, list-group, and badge helpers are tokenized in dark mode.
- No form/route/permission changes.
