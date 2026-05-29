# UI Refresh (Soft-Modular B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the "soft-modular B" aesthetic from `mockups/b-soft-modular.html` across the whole app, make the density tier (`compact / standard / large`) a structural transformation rather than just font scaling, reduce default whitespace on the volunteer-response cards (without breaking mobile), and split task descriptions into a truncated `.summary` (collapsed) plus a full wrapped `.description` (expanded).

**Architecture:** Three-tier rollout. Tier 1 rewrites `app.css` tokens and the widely-used global classes (`.btn`, `.badge`, `.card`, `.data-table`, `.form-field`, header, `.page-*`) — this alone propagates the new look to every page automatically. Tier 2 extracts three reusable Svelte shells (`PageHeader`, `CallCard`, `TaskRow`) and refreshes the existing standalone components (`Select`, `AvatarMenu`, `Breadcrumb`). Tier 3 sweeps each page that has its own `<style>` block, deleting now-dead CSS and adopting the new shells. A density-audit phase at the end catches any component still ignoring the density vars.

**Tech stack:** SvelteKit + Svelte 5 (`$state`, `$props`, `$derived`), TypeScript strict, CSS variables (existing `--rt-*` palette retained, new surface/typography/radius tokens added), `data-density` attribute on `<html>`. No new runtime deps. Google Fonts adds Plus Jakarta Sans alongside the existing DM Serif Display + DM Sans (DM Sans stays as the fallback / table font).

**Source of truth (visual):** `mockups/b-soft-modular.html` — open in a browser to see every interaction the implementation must match. The density toggle in the top-right of that file is the authoritative behavior.

**Decisions locked in (per the conversation that produced this plan):**
- Aesthetic = B (soft-modular). A and C are not implemented.
- Brand colors preserved (`--rt-green`, `--rt-blue`, `--rt-orange`).
- Density tiers do structural restructuring, not just font scaling: compact collapses tasks to a flat borderless list with inline meta; large gives each task its own floating card with shadow halo. Spec is `[data-density=...]` rules in the mockup.
- Task description split: collapsed shows truncated single-line `.summary`; expanded shows full wrapped `.description` with `white-space: pre-line`. Time appears only in the expanded detail, never in collapsed meta.
- "Save draft" was a mockup mistake — do NOT implement.
- "Withdraw an assignment" is deferred — see `todo.md` Deferred section. Do NOT implement here.
- Dark theme stays dropped (already removed; `loadSettings` cleans up stragglers).
- Plan ships as 8 stacked feature branches (`feat/ui-01-...` through `feat/ui-08-...`). Each branch lands on `main` independently; intermediate states must be shippable.

**Out of scope:**
- Aesthetics A and C from the mockups
- New functionality (Withdraw, Save draft, anything else not in current routes)
- Backend changes
- AssignmentSpreadsheet redesign (it's its own beast — flag for follow-up)
- Email template visual refresh (separate concern)

---

## File map

### Created
- `frontend/src/lib/components/PageHeader.svelte` — title + optional accent bar + right-side meta slot.
- `frontend/src/lib/components/CallCard.svelte` — the soft-modular tinted-head card shell (head + controls + body slot + optional footer).
- `frontend/src/lib/components/TaskRow.svelte` — collapsed/expanded task row with checkbox, summary, full description, conflict pill. Replaces `ItemCard.svelte` for this use; ItemCard is deleted at end of phase 3. **Naming conflict:** there is already a `TaskRow.svelte` on `main` (an admin editor used by `/volunteer-calls/[id]`). Phase 2 task 2.3 first renames the existing component to `TaskEditorRow.svelte`, then creates the new shell.
- `frontend/src/lib/components/PageHeader.test.ts`, `CallCard.test.ts`, `TaskRow.test.ts` — minimal Vitest coverage.
- `docs/superpowers/specs/2026-05-29-ui-refresh-soft-modular.md` — symlink-style pointer doc to the mockup (visual specs don't read well as prose).

### Modified
- `frontend/src/app.css` — rewritten in place: new tokens, restructured density tiers, refreshed `.btn` / `.badge` / `.card` / `.data-table` / `.form-field` / `header` / `.page-*` / chrome.
- `frontend/src/routes/+layout.svelte` — topbar adopts new chrome (sticky, blurred, segmented density control moves to AvatarMenu sub-menu).
- `frontend/src/lib/components/Select.svelte` — pill-style trigger that consumes density vars correctly.
- `frontend/src/lib/components/AvatarMenu.svelte` — menu surface adopts soft-modular card style; density control moves under a "Display" sub-section here (replaces the segmented control planned for the topbar).
- `frontend/src/lib/components/Breadcrumb.svelte` — typography + separator refresh.
- `frontend/src/lib/components/ListViewToggle.svelte` — pill-segmented control matching the mockup.
- `frontend/src/routes/volunteering/+page.svelte` — adopts CallCard + TaskRow; deletes most of its 313-line `<style>` block.
- `frontend/src/routes/volunteer-calls/[id]/assign/+page.svelte` — heaviest sweep (508 lines of CSS); spreadsheet styling kept, rest converted.
- `frontend/src/routes/people/+page.svelte`, `people/[id]/+page.svelte` — list + detail sweeps.
- `frontend/src/routes/volunteer-calls/+page.svelte`, `volunteer-calls/[id]/+page.svelte` — list + detail sweeps.
- `frontend/src/routes/profile/+page.svelte` — sweep.
- `frontend/src/routes/settings/+page.svelte`, `login/+page.svelte`, `inbox/+page.svelte`, `reports/+page.svelte`, `verify/+page.svelte` — light passes (delete dead CSS, adopt new shells where they fit).
- `frontend/src/lib/stores/settings.svelte.ts` — no functional change, but a comment update explaining the structural-density contract (compact/standard/large transform layout, not just type).

### Deleted
- `frontend/src/lib/components/ItemCard.svelte` (+ `.test.ts`) — replaced by `TaskRow`. Deletion happens in the last task of phase 3 once no caller remains.

---

## Phase 0: Branch setup

### Task 0.1: Create the stacked-branch chain

**Files:** none yet.

- [ ] **Step 1: Confirm we're on main, clean.**

```bash
git checkout main
git status   # expect: clean
git pull --ff-only
```

- [ ] **Step 2: Create the first feature branch off main.**

```bash
git checkout -b feat/ui-01-tokens-and-base
```

All subsequent phases each cut their own branch off the previous one's tip:

```bash
# When phase 1 lands on main:
git checkout main && git pull --ff-only
git checkout -b feat/ui-02-shared-shells
# …and so on through feat/ui-08-density-audit.
```

This is per the project's documented "Each item below is a feature branch stacked off the previous one" convention in `todo.md`.

---

## Phase 1: Tokens + base classes  *(branch: `feat/ui-01-tokens-and-base`)*

This is the highest-leverage phase: every page that consumes `.btn`, `.badge`, `.card`, `.form-field`, `.data-table`, headers, or the typography tokens automatically picks up the new look. Approximately 60% of the visual change ships here without touching any page-level file.

### Task 1.1: Add Plus Jakarta Sans to the font import

**Files:** Modify `frontend/src/app.css:1` (the existing `@import url(...)`).

- [ ] **Step 1: Replace the font import line.**

```css
@import url("https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap");
```

- [ ] **Step 2: Run frontend, confirm load.**

```bash
make dev   # in another shell
# open http://localhost:5173
# in browser devtools Network tab, confirm Plus+Jakarta+Sans returns 200
```

### Task 1.2: Replace the `:root` token block

**Files:** Modify `frontend/src/app.css:3-96` (the existing `:root` block — keep `--rt-*` palette colors, replace surface/typography/radius/spacing/density tokens).

The new `:root` block. Preserve every `--rt-*` color from the existing file; replace all other tokens.

- [ ] **Step 1: Rewrite `:root`. Final content of `:root`:**

```css
:root {
  /* RT-AFF brand colors — preserved verbatim from prior version */
  --rt-green: #5aad44;
  --rt-green-dark: #478a36;
  --rt-blue: #3a6db5;
  --rt-blue-dark: #2e5a96;
  --rt-blue-light: #4a7ec4;
  --rt-orange: #f5b74e;
  --rt-orange-light: #fad584;
  --rt-dark: #1e2f3d;
  --rt-text: #2a3340;
  --rt-text-light: #555555;
  --rt-text-muted: #7a8290;
  --rt-gray-100: #f5f3ef;
  --rt-gray-200: #e4dfda;
  --rt-gray-300: #cdc7c0;
  --rt-gray-600: #5a5550;
  --rt-white: #ffffff;
  --rt-error: #c03030;
  --rt-error-bg: #fde8e8;
  --rt-error-text: #842029;
  --rt-success: #3a8a3a;
  --rt-success-bg: #d4edda;
  --rt-success-text: #276749;
  --rt-warning: #b87d20;
  --rt-warning-bg: #fef6e6;
  --rt-warning-text: #664d03;
  --rt-info-bg: #cce5ff;
  --rt-info-text: #004085;
  --rt-info-border: #b8daff;
  --rt-checked-bg: #f0faf0;
  --rt-input-bg: #ffffff;
  --rt-input-border: #cbd5e0;
  --rt-overlay-bg: rgba(0, 0, 0, 0.7);

  /* Surfaces — soft-modular layering */
  --surface-1: #ffffff;          /* card background */
  --surface-2: #faf7f1;          /* page background */
  --surface-3: #f1ece2;          /* recessed control background */
  --hairline: rgba(30, 47, 61, 0.08);

  /* Brand tints used for card heads / hover states */
  --tint-blue: rgba(58, 109, 181, 0.07);
  --tint-green: rgba(90, 173, 68, 0.10);
  --tint-orange: rgba(245, 183, 78, 0.14);

  /* Legacy aliases kept so non-converted CSS doesn't break mid-rollout */
  --rt-bg: var(--surface-2);
  --rt-bg-subtle: var(--surface-3);
  --color-primary: var(--rt-blue);
  --color-primary-dark: var(--rt-blue-dark);
  --color-accent: var(--rt-green);
  --color-accent-dark: var(--rt-green-dark);
  --color-highlight: var(--rt-orange);
  --color-bg: var(--surface-2);
  --color-text: var(--rt-text);

  /* Typography */
  --font-display: "DM Serif Display", Georgia, serif;
  --font-body: "Plus Jakarta Sans", "DM Sans", "Segoe UI", Helvetica, sans-serif;
  --font-heading: var(--font-display);  /* legacy alias */

  /* Volunteer-name display budget (preserved — see prior comment in file) */
  --volunteer-name-display-max: 22;
  --volunteer-name-truncate-at: 21;
  --volunteer-name-max-width: calc(var(--volunteer-name-display-max) * 1ch);

  /* Density vars (standard) — see [data-density=*] for overrides */
  --fz-body: 15px;
  --fz-h1: 2rem;
  --fz-h2: 1.05rem;
  --lh-body: 1.55;
  --sp-2: 6px;
  --sp-3: 10px;
  --sp-4: 14px;
  --sp-5: 20px;
  --sp-6: 28px;
  --radius: 12px;
  --radius-sm: 8px;
  --card-pad-y: 14px;
  --card-pad-x: 18px;
  --task-pad-y: 12px;
  --task-pad-x: 16px;
  --task-gap: 8px;
  --check-size: 22px;
  --btn-h: 40px;
  --btn-pad-x: 16px;
  --btn-fz: 0.92rem;
  --heading-weight: 400;

  /* Legacy density aliases — consumed by per-page CSS not yet swept.
     Removed in phase 8. */
  --font-size-body: var(--fz-body);
  --font-size-sm: 0.85rem;
  --font-size-xs: 0.75rem;
  --line-height-body: var(--lh-body);
  --spacing-xs: var(--sp-2);
  --spacing-sm: var(--sp-3);
  --spacing-md: var(--sp-4);
  --spacing-lg: var(--sp-5);
  --spacing-xl: var(--sp-6);
  --card-padding-y: var(--card-pad-y);
  --card-padding-x: var(--card-pad-x);
  --card-radius: var(--radius);
  --btn-min-height: var(--btn-h);
  --btn-padding-y: 10px;
  --btn-padding-x: var(--btn-pad-x);
  --btn-font-size: var(--btn-fz);
  --table-cell-padding: 0.875rem 0.75rem;
  --item-radius: var(--radius-sm);
  --item-gap: var(--task-gap);
  --item-row-height: 52px;
  --item-row-gap: 0.625rem;
  --item-row-padding: var(--task-pad-y) var(--task-pad-x);
  --item-font-size: 0.95rem;
  --check-inner: calc(var(--check-size) - 4px);
  --textarea-min-height: 72px;
}
```

- [ ] **Step 2: Reload `/volunteering` in the browser.**

Expected: layout shifts a little (radii, surface color), no broken pages, no console errors. The legacy aliases keep the per-page CSS working.

### Task 1.3: Restructure the density tiers

**Files:** Modify `frontend/src/app.css:98-159` (replace both `[data-density="large"]` and `[data-density="compact"]` blocks).

- [ ] **Step 1: Replace with the structural-tier overrides.**

```css
[data-density="compact"] {
  --fz-body: 13.5px;
  --fz-h1: 1.55rem;
  --fz-h2: 0.95rem;
  --lh-body: 1.45;
  --sp-2: 4px; --sp-3: 6px; --sp-4: 10px; --sp-5: 14px; --sp-6: 20px;
  --radius: 10px; --radius-sm: 6px;
  --card-pad-y: 10px; --card-pad-x: 14px;
  --task-pad-y: 7px; --task-pad-x: 12px;
  --task-gap: 2px;
  --check-size: 18px;
  --btn-h: 34px; --btn-pad-x: 12px; --btn-fz: 0.85rem;

  --font-size-body: var(--fz-body);
  --font-size-sm: 0.8rem;
  --font-size-xs: 0.7rem;
  --line-height-body: var(--lh-body);
  --spacing-xs: var(--sp-2);
  --spacing-sm: var(--sp-3);
  --spacing-md: var(--sp-4);
  --spacing-lg: var(--sp-5);
  --spacing-xl: var(--sp-6);
  --card-padding-y: var(--card-pad-y);
  --card-padding-x: var(--card-pad-x);
  --card-radius: var(--radius);
  --btn-min-height: var(--btn-h);
  --btn-padding-y: 6px;
  --btn-padding-x: var(--btn-pad-x);
  --btn-font-size: var(--btn-fz);
  --table-cell-padding: 0.5rem 0.5rem;
  --item-radius: var(--radius-sm);
  --item-row-height: 36px;
  --item-row-padding: 4px 10px;
  --item-font-size: 0.85rem;
  --check-inner: 14px;
  --textarea-min-height: 56px;
}

[data-density="large"] {
  --fz-body: 17px;
  --fz-h1: 2.5rem;
  --fz-h2: 1.2rem;
  --lh-body: 1.65;
  --sp-2: 8px; --sp-3: 14px; --sp-4: 18px; --sp-5: 26px; --sp-6: 36px;
  --radius: 16px; --radius-sm: 12px;
  --card-pad-y: 20px; --card-pad-x: 24px;
  --task-pad-y: 18px; --task-pad-x: 22px;
  --task-gap: 12px;
  --check-size: 26px;
  --btn-h: 48px; --btn-pad-x: 22px; --btn-fz: 1rem;
  --heading-weight: 700;

  --font-size-body: var(--fz-body);
  --font-size-sm: 0.95rem;
  --font-size-xs: 0.85rem;
  --line-height-body: var(--lh-body);
  --spacing-xs: var(--sp-2);
  --spacing-sm: var(--sp-3);
  --spacing-md: var(--sp-4);
  --spacing-lg: var(--sp-5);
  --spacing-xl: var(--sp-6);
  --card-padding-y: var(--card-pad-y);
  --card-padding-x: var(--card-pad-x);
  --card-radius: var(--radius);
  --btn-min-height: var(--btn-h);
  --btn-padding-y: 14px;
  --btn-padding-x: var(--btn-pad-x);
  --btn-font-size: var(--btn-fz);
  --table-cell-padding: 1rem 0.875rem;
  --item-radius: var(--radius-sm);
  --item-row-height: 60px;
  --item-row-padding: 14px 20px;
  --item-font-size: 1.05rem;
  --check-inner: 22px;
  --textarea-min-height: 96px;
  --rt-text: #1f262f;
}
```

The actual *structural* density transformation (per-task card halo on large, flat list on compact) is delivered in `TaskRow.svelte` (phase 2). The tokens above provide the type/spacing axis the structural rules layer onto.

### Task 1.4: Rewrite the page background + body + headings

**Files:** Modify `frontend/src/app.css:161-200` (body, h1-h6, .app).

- [ ] **Step 1: Replace the body / headings block.**

```css
* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--fz-body);
  background:
    radial-gradient(1200px 600px at 90% -10%, var(--tint-green), transparent 60%),
    radial-gradient(900px 500px at -10% 30%, var(--tint-blue), transparent 60%),
    var(--surface-2);
  background-attachment: fixed;
  color: var(--color-text);
  line-height: var(--lh-body);
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-display);
  color: var(--rt-dark);
  letter-spacing: -0.3px;
  font-weight: var(--heading-weight);
}

a { color: var(--color-primary); text-decoration: none; }
a:hover { text-decoration: underline; }

.app { display: flex; flex-direction: column; min-height: 100vh; }
```

### Task 1.5: Rewrite the topbar / header

**Files:** Modify `frontend/src/app.css:202-268` (header rules).

- [ ] **Step 1: Replace with the soft-modular topbar.**

```css
header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--hairline);
  padding: 10px var(--sp-5);
  display: flex;
  align-items: center;
  gap: var(--sp-4);
}
header .logo { flex: 0 0 auto; display: flex; align-items: center; text-decoration: none; }
header .logo img { height: 36px; width: auto; }

header nav {
  flex: 1;
  display: flex;
  gap: 4px;
  align-items: center;
  justify-content: center;
}

header nav a {
  color: var(--rt-text);
  font-weight: 600;
  font-size: 0.92rem;
  padding: 8px 14px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: background-color 0.15s, color 0.15s;
}
header nav a:hover {
  background: var(--surface-3);
  color: var(--rt-dark);
  text-decoration: none;
}
header nav a.active {
  background: var(--tint-blue);
  color: var(--rt-blue-dark);
}
header nav .nav-icon { font-size: 1.25rem; line-height: 1; }
```

### Task 1.6: Rewrite buttons

**Files:** Modify `frontend/src/app.css:373-447` (the entire `.btn*` block).

- [ ] **Step 1: Replace the button rules.**

```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: var(--btn-h);
  padding: 0 var(--btn-pad-x);
  border: 0;
  border-radius: 999px;
  font-family: var(--font-body);
  font-weight: 600;
  font-size: var(--btn-fz);
  background: var(--surface-3);
  color: var(--rt-text);
  cursor: pointer;
  text-decoration: none;
  transition: transform 0.1s, box-shadow 0.15s, background-color 0.15s;
  box-shadow: 0 1px 0 rgba(0,0,0,.04);
}
.btn:hover { text-decoration: none; transform: translateY(-1px); box-shadow: 0 4px 12px -6px rgba(30,47,61,.25); }
.btn:active { transform: translateY(0); box-shadow: inset 0 1px 3px rgba(0,0,0,.12); }
.btn:disabled { opacity: 0.55; cursor: not-allowed; transform: none; box-shadow: none; }

.btn-primary { background: var(--rt-blue); color: white; box-shadow: 0 1px 0 rgba(0,0,0,.04), 0 4px 12px -6px rgba(58,109,181,.5); }
.btn-primary:hover { background: var(--rt-blue-dark); }

.btn-accent { background: var(--rt-green); color: white; box-shadow: 0 1px 0 rgba(0,0,0,.04), 0 4px 12px -6px rgba(90,173,68,.5); }
.btn-accent:hover { background: var(--rt-green-dark); }

.btn-secondary { background: var(--surface-3); color: var(--rt-text); }
.btn-secondary:hover { background: var(--rt-gray-200); }

.btn-danger { background: var(--rt-error); color: white; }
.btn-danger:hover { background: #a02828; }

.btn-ghost { background: transparent; color: var(--rt-text-muted); box-shadow: none; }
.btn-ghost:hover { background: var(--surface-3); color: var(--rt-dark); transform: none; box-shadow: none; }

.btn-small, .btn-sm {
  min-height: 32px;
  padding: 0 12px;
  font-size: var(--font-size-sm);
}
```

`.btn-sm` is a new alias because the codebase has both `.btn-small` and `.btn-sm` in use (grep first to verify — the rule above adds the alias so no rename is needed).

### Task 1.7: Rewrite cards, badges, data-table, form fields

**Files:** Modify `frontend/src/app.css:452-575` (cards through form-field).

- [ ] **Step 1: Cards.**

```css
.card {
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  padding: var(--card-pad-y) var(--card-pad-x);
  box-shadow: 0 1px 0 rgba(255,255,255,.6) inset, 0 8px 24px -16px rgba(30,47,61,.12);
}
.card h2 {
  margin: 0 0 var(--sp-4) 0;
  font-family: var(--font-body);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--rt-text-muted);
}

.section-card {
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  padding: var(--card-pad-y) var(--card-pad-x);
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.15s, transform 0.15s;
  display: block;
}
.section-card:not(.disabled):hover {
  box-shadow: 0 8px 24px -16px rgba(30,47,61,.25);
  transform: translateY(-1px);
  text-decoration: none;
}
.section-card:not(.disabled):active { transform: translateY(0); }
```

- [ ] **Step 2: Badges (preserve every existing color modifier; only the base rule changes).**

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-transform: capitalize;
  background: var(--surface-3);
  color: var(--rt-text);
}
/* The .badge-* color modifiers from the prior file stay verbatim. */
```

- [ ] **Step 3: Data table.**

```css
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td {
  padding: var(--table-cell-padding);
  text-align: left;
  border-bottom: 1px solid var(--hairline);
}
.data-table th {
  background: transparent;
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 0.72rem;
  color: var(--rt-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.data-table tbody tr:hover { background: var(--surface-2); }
```

- [ ] **Step 4: Form fields.**

```css
.form-field {
  display: flex;
  flex-direction: column;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--rt-text-muted);
  flex: 1;
}
.form-field input,
.form-field select,
.form-field textarea {
  margin-top: var(--sp-2);
  padding: 0 var(--sp-4);
  min-height: var(--btn-h);
  border: 1px solid var(--rt-input-border);
  border-radius: var(--radius-sm);
  background: var(--rt-input-bg);
  color: var(--color-text);
  font-size: var(--fz-body);
  font-family: var(--font-body);
  font-weight: 400;
}
.form-field textarea { padding: var(--sp-3) var(--sp-4); min-height: var(--textarea-min-height); }
.form-field input:focus,
.form-field select:focus,
.form-field textarea:focus {
  outline: none;
  border-color: var(--rt-blue);
  box-shadow: 0 0 0 3px rgba(58,109,181,.18);
}
```

### Task 1.8: Snapshot the visual baseline + commit phase 1

- [ ] **Step 1: Visual smoke test — every route.**

```bash
make dev   # in another shell
```

In the browser, visit each of these and confirm: no console errors, layouts render, buttons / badges / cards look refreshed:
- `/` (home)
- `/login` (logged out → use the seeded test user)
- `/volunteering`
- `/volunteer-calls`
- `/volunteer-calls/<some-id>`
- `/volunteer-calls/<some-id>/assign` (staff session)
- `/people`
- `/people/<some-id>`
- `/profile`
- `/settings`
- `/inbox`
- `/reports`

- [ ] **Step 2: Run lint + test.**

```bash
make lint-fe
make test-frontend
```

Expected: pass. If `format:check` fails on `app.css`, run `make format-fe` and re-stage.

- [ ] **Step 3: Run the headless demo smoke (catches major layout regressions).**

```bash
# In one shell:
make dev
# In another, once stack is up:
make test-e2e
```

Expected: pass.

- [ ] **Step 4: Commit.**

```bash
git add frontend/src/app.css
git commit -m "ui: refresh tokens + base classes to soft-modular B

Phase 1 of UI refresh. Rewrites :root, density tiers, header, body,
.btn, .card, .badge, .data-table, .form-field. Per-page CSS keeps
working via legacy aliases (--card-padding-*, --spacing-*, etc.) that
forward to the new tokens; aliases are removed in phase 8.

Spec: mockups/b-soft-modular.html.
Plan: docs/superpowers/plans/2026-05-29-ui-refresh-soft-modular.md."
```

- [ ] **Step 5: Merge to main, advance branch chain.**

```bash
git checkout main
git merge --no-ff feat/ui-01-tokens-and-base
git push origin main
git checkout -b feat/ui-02-shared-shells
```

---

## Phase 2: Shared shells  *(branch: `feat/ui-02-shared-shells`)*

Extract the soft-modular shapes from the mockup into Svelte components. Phase 3 then consumes these in `volunteering/+page.svelte`; later phases reuse them elsewhere.

### Task 2.1: `PageHeader.svelte`

**Files:** Create `frontend/src/lib/components/PageHeader.svelte`, `frontend/src/lib/components/PageHeader.test.ts`.

- [ ] **Step 1: Write the failing test first.**

`frontend/src/lib/components/PageHeader.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { render } from "@testing-library/svelte";
import PageHeader from "./PageHeader.svelte";

describe("PageHeader", () => {
  it("renders the title", () => {
    const { getByRole } = render(PageHeader, { props: { title: "Volunteering" } });
    expect(getByRole("heading", { level: 1 })).toHaveTextContent("Volunteering");
  });

  it("omits the meta region when no meta snippet is passed", () => {
    const { container } = render(PageHeader, { props: { title: "Hi" } });
    expect(container.querySelector(".page-header-meta")).toBeNull();
  });
});
```

- [ ] **Step 2: Verify it fails.**

```bash
cd frontend && pnpm exec vitest run src/lib/components/PageHeader.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement.**

`frontend/src/lib/components/PageHeader.svelte`:

```svelte
<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    meta,
  }: {
    title: string;
    meta?: Snippet;
  } = $props();
</script>

<header class="page-header">
  <div class="title-row">
    <span class="accent" aria-hidden="true"></span>
    <h1>{title}</h1>
  </div>
  {#if meta}
    <div class="page-header-meta">{@render meta()}</div>
  {/if}
</header>

<style>
  .page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: var(--sp-4);
    margin-bottom: var(--sp-5);
  }
  .title-row { display: flex; align-items: baseline; gap: 12px; }
  .accent {
    display: inline-block;
    width: 22px; height: 4px;
    border-radius: 2px;
    background: var(--rt-green);
    margin-bottom: 6px;
  }
  h1 { margin: 0; font-size: var(--fz-h1); }
  .page-header-meta { color: var(--rt-text-muted); font-size: 0.85rem; font-variant-numeric: tabular-nums; }
</style>
```

- [ ] **Step 4: Verify pass.**

```bash
pnpm exec vitest run src/lib/components/PageHeader.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add frontend/src/lib/components/PageHeader.svelte frontend/src/lib/components/PageHeader.test.ts
git commit -m "ui: add PageHeader shell"
```

### Task 2.2: `CallCard.svelte`

**Files:** Create `frontend/src/lib/components/CallCard.svelte`, `frontend/src/lib/components/CallCard.test.ts`.

- [ ] **Step 1: Write the failing test.**

`frontend/src/lib/components/CallCard.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { render } from "@testing-library/svelte";
import CallCard from "./CallCard.svelte";
import { createRawSnippet } from "svelte";

const snippet = (html: string) =>
  createRawSnippet(() => ({ render: () => html }));

describe("CallCard", () => {
  it("renders title and meta in the head", () => {
    const { getByText } = render(CallCard, {
      props: {
        title: "Coastal cleanup",
        meta: "5 tasks",
        body: snippet("<p>body</p>"),
      },
    });
    expect(getByText("Coastal cleanup")).toBeInTheDocument();
    expect(getByText("5 tasks")).toBeInTheDocument();
  });

  it("renders body snippet content", () => {
    const { container } = render(CallCard, {
      props: { title: "X", body: snippet("<p data-testid=body>hello</p>") },
    });
    expect(container.querySelector('[data-testid="body"]')).toHaveTextContent("hello");
  });
});
```

- [ ] **Step 2: Verify fails.**

```bash
pnpm exec vitest run src/lib/components/CallCard.test.ts
```

Expected: FAIL.

- [ ] **Step 3: Implement.**

`frontend/src/lib/components/CallCard.svelte`:

```svelte
<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    meta,
    controls,
    body,
    footer,
  }: {
    title: string;
    meta?: string;
    controls?: Snippet;
    body: Snippet;
    footer?: Snippet;
  } = $props();
</script>

<article class="call">
  <header class="call-head">
    <span class="call-title">{title}</span>
    {#if meta}<span class="call-meta">{meta}</span>{/if}
  </header>
  {#if controls}
    <div class="call-controls">{@render controls()}</div>
  {/if}
  <div class="call-body">{@render body()}</div>
  {#if footer}
    <div class="call-footer">{@render footer()}</div>
  {/if}
</article>

<style>
  .call {
    background: var(--surface-1);
    border-radius: var(--radius);
    border: 1px solid var(--hairline);
    box-shadow: 0 2px 12px -8px rgba(30,47,61,.15);
    overflow: hidden;
    margin-bottom: var(--sp-4);
  }
  .call-head {
    display: flex; align-items: center; gap: var(--sp-3);
    padding: var(--card-pad-y) var(--card-pad-x);
    background: linear-gradient(180deg, var(--tint-blue), transparent);
    border-bottom: 1px solid var(--hairline);
  }
  .call-title {
    font-family: var(--font-display);
    font-size: 1.18rem;
    color: var(--rt-dark);
    font-weight: var(--heading-weight);
  }
  .call-meta {
    margin-left: auto;
    font-size: 0.78rem;
    color: var(--rt-text-muted);
    background: var(--surface-3);
    padding: 4px 10px;
    border-radius: 999px;
    font-weight: 600;
  }
  .call-controls {
    display: flex; align-items: center; gap: var(--sp-4);
    padding: var(--sp-3) var(--card-pad-x);
    border-bottom: 1px solid var(--hairline);
    flex-wrap: wrap;
  }
  .call-footer {
    padding: var(--sp-4) var(--card-pad-x) var(--card-pad-y);
    border-top: 1px solid var(--hairline);
    display: flex; gap: var(--sp-3); justify-content: flex-end;
  }
</style>
```

- [ ] **Step 4: Verify pass.**

```bash
pnpm exec vitest run src/lib/components/CallCard.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add frontend/src/lib/components/CallCard.svelte frontend/src/lib/components/CallCard.test.ts
git commit -m "ui: add CallCard shell"
```

### Task 2.3: `TaskRow.svelte` (replaces ItemCard)

**Files:** Create `frontend/src/lib/components/TaskRow.svelte`, `frontend/src/lib/components/TaskRow.test.ts`.

The most important component in this phase. It carries: collapsed/expanded toggle, `summary` truncation, full wrapped `description`, conflict pill, checkbox, density restructuring rules.

- [ ] **Step 1: Write failing tests.**

`frontend/src/lib/components/TaskRow.test.ts`:

```typescript
import { describe, expect, it, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import TaskRow from "./TaskRow.svelte";

const baseProps = {
  name: "Driftwood collection",
  summary: "Stage driftwood pulled from the upper beach into the sort pile…",
  description: "Stage driftwood pulled from the upper beach into the sort pile by the lot.\n\nAnything over 6 ft. goes to the structural side.",
  city: "Pacifica",
  date: "Sat Jun 21",
  checked: false,
  expanded: false,
};

describe("TaskRow", () => {
  it("shows the summary when collapsed and hides the description", () => {
    const { getByText, queryByText } = render(TaskRow, { props: baseProps });
    expect(getByText(/Stage driftwood pulled from the upper beach/)).toBeInTheDocument();
    // Full description text after the first line is not in the DOM (display:none on detail)
    expect(queryByText(/structural side/)).not.toBeVisible();
  });

  it("shows the full description when expanded and hides the summary", () => {
    const { container, getByText } = render(TaskRow, { props: { ...baseProps, expanded: true } });
    expect(getByText(/structural side/)).toBeInTheDocument();
    // summary is now display:none via CSS
    const summary = container.querySelector(".task-summary") as HTMLElement;
    expect(getComputedStyle(summary).display).toBe("none");
  });

  it("does NOT show time in the collapsed meta (lives in expanded detail only)", () => {
    const props = { ...baseProps, time: "10:00–13:00" };
    const { container } = render(TaskRow, { props });
    const meta = container.querySelector(".task-meta")!;
    expect(meta.textContent).not.toContain("10:00");
  });

  it("fires onToggleChecked when the checkbox changes", async () => {
    const onToggleChecked = vi.fn();
    const { container } = render(TaskRow, { props: { ...baseProps, onToggleChecked } });
    const cb = container.querySelector("input[type=checkbox]") as HTMLInputElement;
    await fireEvent.click(cb);
    expect(onToggleChecked).toHaveBeenCalledOnce();
  });

  it("fires onToggleExpanded when the row body is clicked", async () => {
    const onToggleExpanded = vi.fn();
    const { container } = render(TaskRow, { props: { ...baseProps, onToggleExpanded } });
    const body = container.querySelector(".task-body") as HTMLElement;
    await fireEvent.click(body);
    expect(onToggleExpanded).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Verify fails.**

```bash
pnpm exec vitest run src/lib/components/TaskRow.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement.**

`frontend/src/lib/components/TaskRow.svelte`:

```svelte
<script lang="ts">
  let {
    name,
    summary,
    description,
    city,
    date,
    time,
    volunteersNeeded,
    skilledNeeded = 0,
    notes,
    checked = false,
    expanded = false,
    conflict = false,
    conflictTitle = "",
    onToggleChecked,
    onToggleExpanded,
  }: {
    name: string;
    summary: string;
    description?: string;
    city?: string;
    date?: string;
    time?: string;
    volunteersNeeded?: number;
    skilledNeeded?: number;
    notes?: string;
    checked?: boolean;
    expanded?: boolean;
    conflict?: boolean;
    conflictTitle?: string;
    onToggleChecked?: () => void;
    onToggleExpanded?: () => void;
  } = $props();

  function bodyKey(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onToggleExpanded?.();
    }
  }
</script>

<li class="task" class:checked class:expanded>
  <input
    type="checkbox"
    class="task-check"
    {checked}
    onchange={() => onToggleChecked?.()}
    aria-label={`Toggle ${name}`}
  />

  <div
    class="task-body"
    role="button"
    tabindex="0"
    aria-expanded={expanded}
    onclick={() => onToggleExpanded?.()}
    onkeydown={bodyKey}
  >
    <div class="task-name">
      {name}
      {#if conflict}
        <span class="conflict-flag" title={conflictTitle}>⚠ calendar conflict</span>
      {/if}
    </div>
    <div class="task-summary">{summary}</div>
    <div class="task-meta">
      {#if city}{city}{/if}
      {#if city && date} · {/if}
      {#if date}{date}{/if}
    </div>
  </div>

  <button
    type="button"
    class="task-expand"
    aria-label={expanded ? "Collapse" : "Expand"}
    onclick={() => onToggleExpanded?.()}
  >
    <span class="chev" class:open={expanded} aria-hidden="true">▾</span>
  </button>

  <dl class="task-detail">
    {#if description}
      <dd class="task-description">{description}</dd>
    {/if}
    {#if time}<dt>Time</dt><dd>{time}</dd>{/if}
    {#if volunteersNeeded != null}<dt>Volunteers needed</dt><dd>{volunteersNeeded}</dd>{/if}
    {#if skilledNeeded > 0}<dt>Skilled needed</dt><dd>{skilledNeeded}</dd>{/if}
    {#if notes}<dt>Notes</dt><dd>{notes}</dd>{/if}
  </dl>
</li>

<style>
  .task {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: var(--sp-3);
    padding: var(--task-pad-y) var(--task-pad-x);
    border-radius: var(--radius-sm);
    background: var(--surface-2);
    border: 1px solid transparent;
    transition: background 0.15s, border-color 0.15s, transform 0.15s;
  }
  .task:hover { background: var(--surface-1); border-color: var(--hairline); }
  .task.checked {
    background: linear-gradient(180deg, var(--tint-green), transparent), var(--surface-1);
    border-color: rgba(90,173,68,.35);
  }

  .task-check {
    appearance: none; -webkit-appearance: none;
    width: var(--check-size); height: var(--check-size);
    border-radius: 6px;
    border: 1.5px solid #c5cad2;
    background: var(--surface-1);
    cursor: pointer;
    display: grid; place-items: center;
    transition: background 0.15s, border-color 0.15s;
  }
  .task-check:checked {
    background: linear-gradient(135deg, var(--rt-green), var(--rt-green-dark));
    border-color: var(--rt-green-dark);
  }
  .task-check:checked::after { content: "✓"; color: white; font-size: 0.78em; font-weight: 800; }

  .task-body { min-width: 0; cursor: pointer; }
  .task-name { font-weight: 600; color: var(--rt-dark); display: flex; align-items: center; gap: 6px; }
  .task-summary {
    font-size: 0.92em;
    color: var(--rt-text);
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    line-clamp: 1;
    -webkit-box-orient: vertical;
  }
  .task.expanded .task-summary { display: none; }
  .task-meta { font-size: 0.82em; color: var(--rt-text-muted); margin-top: 2px; }
  .conflict-flag {
    font-size: 0.7rem; padding: 2px 7px; border-radius: 999px;
    background: var(--tint-orange); color: #8c5a10; font-weight: 600;
  }

  .task-expand {
    appearance: none; border: 0; background: transparent; cursor: pointer;
    width: 32px; height: 32px; border-radius: 8px; color: var(--rt-text-muted);
    display: grid; place-items: center; transition: background 0.15s;
  }
  .task-expand:hover { background: var(--surface-3); }
  .chev { display: inline-block; transition: transform 0.2s; }
  .chev.open { transform: rotate(180deg); }

  .task-detail {
    grid-column: 1 / -1;
    margin: var(--sp-3) 0 0;
    padding: var(--sp-3) 0 0;
    border-top: 1px solid var(--hairline);
    display: grid; grid-template-columns: max-content 1fr;
    gap: 4px var(--sp-4);
    font-size: 0.9em;
  }
  .task-detail dt { color: var(--rt-text-muted); font-weight: 500; }
  .task-detail dd { margin: 0; color: var(--rt-text); }
  .task-description {
    grid-column: 1 / -1;
    margin: 0 0 var(--sp-3) 0;
    color: var(--rt-text);
    line-height: 1.55;
    white-space: pre-line;
  }
  .task:not(.expanded) .task-detail { display: none; }

  /* Density: compact = flat borderless row, inline meta */
  :global([data-density="compact"]) .task {
    background: transparent;
    border-radius: 0;
    border-top: 1px solid var(--hairline);
    padding: 8px 14px;
    grid-template-columns: auto 1fr auto auto;
    align-items: center;
  }
  :global([data-density="compact"]) .task.checked { background: rgba(90,173,68,.08); }
  :global([data-density="compact"]) .task-body { display: flex; align-items: baseline; gap: 10px; }
  :global([data-density="compact"]) .task-summary { display: none; }
  :global([data-density="compact"]) .task-meta { margin: 0 0 0 auto; white-space: nowrap; }

  /* Density: large = floating card with shadow halo */
  :global([data-density="large"]) .task {
    background: var(--surface-1);
    border: 1px solid var(--hairline);
    box-shadow: 0 1px 0 rgba(255,255,255,1), 0 2px 8px -6px rgba(30,47,61,.15);
  }
  :global([data-density="large"]) .task:hover {
    transform: translateY(-1px);
    box-shadow: 0 1px 0 rgba(255,255,255,1), 0 6px 18px -10px rgba(30,47,61,.25);
  }
</style>
```

- [ ] **Step 4: Verify pass.**

```bash
pnpm exec vitest run src/lib/components/TaskRow.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add frontend/src/lib/components/TaskRow.svelte frontend/src/lib/components/TaskRow.test.ts
git commit -m "ui: add TaskRow shell (replaces ItemCard for task lists)

Carries collapsed summary + expanded description + meta + conflict pill +
density restructuring (compact flat list, large floating cards with halo)."
```

### Task 2.4: Refresh `Select.svelte` to the pill-trigger style

**Files:** Modify `frontend/src/lib/components/Select.svelte`. Tests in `Select.test.ts` already exist — they must continue to pass.

- [ ] **Step 1: Read existing test to know what API to preserve.**

```bash
cat frontend/src/lib/components/Select.test.ts
```

The test exercises `value`, `options`, `onchange`, `ariaLabel`, `placeholder`. Preserve all of those.

- [ ] **Step 2: Refresh the trigger styling to the pill shape from the mockup, keeping the existing component logic.**

Within `Select.svelte`'s `<style>` block, replace the trigger button rule with:

```css
.select-trigger {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 28px 6px 12px;
  background: var(--surface-2);
  border: 1px solid var(--hairline);
  border-radius: 999px;
  font: inherit;
  font-weight: 600;
  color: var(--rt-dark);
  min-height: var(--btn-h);
  cursor: pointer;
  background-image:
    linear-gradient(45deg, transparent 50%, var(--rt-text-muted) 50%),
    linear-gradient(135deg, var(--rt-text-muted) 50%, transparent 50%);
  background-position: calc(100% - 14px) 50%, calc(100% - 9px) 50%;
  background-size: 5px 5px, 5px 5px;
  background-repeat: no-repeat;
}
.select-trigger:hover { background-color: var(--surface-1); }
.select-trigger:focus { outline: none; box-shadow: 0 0 0 3px rgba(58,109,181,.18); border-color: var(--rt-blue); }
```

Within the popup surface rule:

```css
.select-popup {
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  box-shadow: 0 12px 32px -16px rgba(30,47,61,.3);
  padding: 4px;
}
.select-option {
  padding: 8px 12px;
  border-radius: calc(var(--radius-sm) - 4px);
  cursor: pointer;
}
.select-option:hover, .select-option[aria-selected="true"] { background: var(--surface-2); }
```

(If the existing class names differ, grep the file first and adapt — don't rename, just restyle.)

- [ ] **Step 3: Run Select tests + interactive smoke.**

```bash
pnpm exec vitest run src/lib/components/Select.test.ts
make dev  # in another shell — open /people, change the role filter
```

Expected: tests pass; the role filter dropdown opens and looks pill-shaped.

- [ ] **Step 4: Commit.**

```bash
git add frontend/src/lib/components/Select.svelte
git commit -m "ui: pill-style Select trigger + soft-modular popup"
```

### Task 2.5: Refresh `AvatarMenu.svelte` + move the density control into it

**Files:** Modify `frontend/src/lib/components/AvatarMenu.svelte`. Tests in `AvatarMenu.test.ts` exist.

Per the locked-in decisions, the density toggle lives inside the avatar menu (the prior plan suggested topbar, which would crowd the chrome). This task wires it.

- [ ] **Step 1: Read the existing menu shape to preserve the staff/non-staff conditional sections.**

```bash
cat frontend/src/lib/components/AvatarMenu.svelte
```

- [ ] **Step 2: Restyle the popover surface to the soft-modular card.**

```css
.avatar-menu {
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  box-shadow: 0 16px 40px -16px rgba(30,47,61,.35);
  padding: 6px;
  min-width: 240px;
}
.avatar-menu .group { padding: 4px; }
.avatar-menu .group + .group { border-top: 1px solid var(--hairline); margin-top: 4px; padding-top: 8px; }
.avatar-menu a, .avatar-menu button.menu-item {
  display: flex; align-items: center; gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 0; cursor: pointer;
  color: var(--rt-text); text-decoration: none;
  font: inherit; font-weight: 500;
  text-align: left;
}
.avatar-menu a:hover, .avatar-menu button.menu-item:hover { background: var(--surface-2); }
```

- [ ] **Step 3: Add a "Display" group with a 3-segment density picker.**

In the menu template, add after the Settings/Inbox group:

```svelte
{#snippet densitySeg(value: "compact" | "standard" | "large", label: string)}
  <button
    type="button"
    class="density-opt"
    aria-pressed={settingsState.density === value}
    onclick={() => { settingsState.density = value; applySettings(); }}
  >{label}</button>
{/snippet}

<div class="group density-group">
  <div class="group-label">Display density</div>
  <div class="density-seg" role="radiogroup" aria-label="Display density">
    {@render densitySeg("compact", "Compact")}
    {@render densitySeg("standard", "Standard")}
    {@render densitySeg("large", "Large")}
  </div>
</div>
```

with these styles appended to the component's `<style>`:

```css
.group-label {
  padding: 0 8px 4px;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--rt-text-muted);
  font-weight: 600;
}
.density-seg {
  display: inline-flex;
  background: var(--surface-2);
  border-radius: 999px;
  padding: 3px;
  width: 100%;
}
.density-opt {
  appearance: none; border: 0; background: transparent;
  flex: 1;
  padding: 6px 10px;
  border-radius: 999px;
  font: inherit; font-size: 0.82rem; font-weight: 600;
  color: var(--rt-text-muted);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.density-opt[aria-pressed="true"] {
  background: var(--surface-1);
  color: var(--rt-dark);
  box-shadow: 0 1px 0 var(--hairline), 0 1px 3px rgba(0,0,0,.04);
}
```

The script block needs:

```typescript
import { settingsState, applySettings } from "$lib/stores/settings.svelte";
```

- [ ] **Step 4: If the `/settings` page also has a density picker, leave it there for now** — both surfaces are valid; phase 7's settings sweep decides whether to remove the page-level one.

- [ ] **Step 5: Run AvatarMenu tests + manual smoke.**

```bash
pnpm exec vitest run src/lib/components/AvatarMenu.test.ts
# In dev: click the avatar, confirm density picker appears and switching
# it visibly reflows /volunteering in real time.
```

- [ ] **Step 6: Commit.**

```bash
git add frontend/src/lib/components/AvatarMenu.svelte
git commit -m "ui: soft-modular AvatarMenu + density picker inside it"
```

### Task 2.6: Refresh `Breadcrumb.svelte` + `ListViewToggle.svelte`

**Files:** Modify both components' `<style>` blocks only — markup unchanged.

- [ ] **Step 1: Breadcrumb — use muted text + chevron separator.**

```css
.breadcrumb { display: flex; align-items: center; gap: 6px; font-size: 0.85rem; color: var(--rt-text-muted); }
.breadcrumb a { color: var(--rt-text-muted); }
.breadcrumb a:hover { color: var(--rt-blue); text-decoration: none; }
.breadcrumb .sep { color: var(--rt-text-muted); opacity: 0.5; }
.breadcrumb .current { color: var(--rt-dark); font-weight: 600; }
```

- [ ] **Step 2: ListViewToggle — pill-segmented control matching the mockup's view-toggle.**

```css
.view-toggle { display: inline-flex; gap: 2px; background: var(--surface-2); padding: 3px; border-radius: 8px; }
.view-toggle button {
  appearance: none; border: 0; padding: 5px 12px;
  font: inherit; font-size: 0.82rem; font-weight: 600;
  background: transparent; color: var(--rt-text-muted);
  border-radius: 6px; cursor: pointer;
}
.view-toggle button.active { background: var(--surface-1); color: var(--rt-dark); }
```

- [ ] **Step 3: Tests + commit.**

```bash
pnpm exec vitest run src/lib/components/Breadcrumb.test.ts src/lib/components/ListViewToggle.test.ts
git add frontend/src/lib/components/Breadcrumb.svelte frontend/src/lib/components/ListViewToggle.svelte
git commit -m "ui: refresh Breadcrumb + ListViewToggle styling"
```

### Task 2.7: Phase 2 verification + merge

- [ ] **Step 1: Run full frontend lint + tests + e2e smoke.**

```bash
make lint-fe
make test-frontend
make test-e2e
```

- [ ] **Step 2: Merge to main.**

```bash
git checkout main
git merge --no-ff feat/ui-02-shared-shells
git push origin main
git checkout -b feat/ui-03-volunteering
```

---

## Phase 3: Volunteering page  *(branch: `feat/ui-03-volunteering`)*

Adopt the new shells in the page the user spends the most time on. Most of the 313-line `<style>` block deletes here.

### Task 3.1: Add the description field to the API contract

The task description split assumes the backend exposes both a short summary-source and a long description. Check the current `Task` schema.

**Files:** Read `backend/src/volunteer_call_api/schemas/jobs.py` (or wherever the `JobListItem` is defined — grep for `short_description`).

- [ ] **Step 1: Locate the type.**

```bash
grep -rn "short_description" backend/src
```

- [ ] **Step 2: Decision tree.**

- **If a long `description` field already exists** on the Task model and just isn't exposed: add it to `JobListItem`, regenerate types (`make types`), and skip to task 3.2.
- **If no long-description field exists:** the database needs a `description: TEXT NULL` column on `task`, an Alembic migration, schema field add, and `short_description` becomes a `derived` (first ~150 chars of `description` with ellipsis when truncated). This is a backend change — extract into its own micro-branch `feat/ui-03a-task-description-field` *before* continuing.

In either case, the frontend code in tasks 3.2+ assumes `job.short_description` (collapsed summary, ≤~150 chars) and `job.description` (full text) are both present.

- [ ] **Step 3: If a migration was needed, run it locally and commit it on the prep branch, merge that branch, then return here.**

### Task 3.2: Swap volunteering page markup to the new shells

**Files:** Modify `frontend/src/routes/volunteering/+page.svelte`.

- [ ] **Step 1: Add new imports.**

```typescript
import PageHeader from '$lib/components/PageHeader.svelte';
import CallCard from '$lib/components/CallCard.svelte';
import TaskRow from '$lib/components/TaskRow.svelte';
```

Remove the `import ItemCard from '$lib/components/ItemCard.svelte';` line.

- [ ] **Step 2: Replace the `<h1>Volunteering</h1>` with `<PageHeader title="Volunteering" />`.**

- [ ] **Step 3: Replace each call's outer markup with `<CallCard>`.**

The template change (current `<div class="call-section">…<div class="call-header">…` block becomes):

```svelte
<CallCard
  title={call.title}
  meta={`${call.task_count} task${call.task_count === 1 ? '' : 's'}`}
>
  {#snippet controls()}
    <!-- max-week-row + ListViewToggle from the current template, unchanged -->
  {/snippet}
  {#snippet body()}
    {#if banner}
      <div class="call-banner call-banner-{banner.tone}" role="status">{banner.text}</div>
    {/if}
    {#if loadingCalls.has(call.id)}
      <p class="loading-text">Loading tasks...</p>
    {:else}
      <!-- jobs / table view / card view -->
    {/if}
  {/snippet}
  {#snippet footer()}
    {#if saveMessage[call.id]}
      <div class="success-banner">{saveMessage[call.id]}</div>
    {/if}
    {#if canSubmit}
      <button class="btn btn-primary submit-btn" onclick={() => submitAvailability(call.id)} disabled={saving[call.id]}>
        <!-- existing label logic -->
      </button>
    {/if}
  {/snippet}
</CallCard>
```

- [ ] **Step 4: Replace each `<ItemCard>` with `<TaskRow>`.**

```svelte
<TaskRow
  name={job.short_description}
  summary={job.short_description}
  description={job.description}
  city={job.city ?? undefined}
  date={job.date ? formatDate(job.date) : 'Unscheduled'}
  time={formatTimeRange(job.time_start, job.time_end) || undefined}
  volunteersNeeded={job.volunteers_needed}
  skilledNeeded={job.skilled_needed}
  notes={job.notes ?? undefined}
  checked={selected.has(job.task_id)}
  expanded={expandedTasks.has(job.task_id)}
  conflict={!!conflict?.has_conflict}
  conflictTitle={conflict?.conflicts?.map(c => c.summary ?? 'Calendar event').join('; ') ?? ''}
  onToggleChecked={() => toggleTask(call.id, job.task_id)}
  onToggleExpanded={() => toggleExpand(job.task_id)}
/>
```

**Note:** the previous markup had separate `task-row` / `task-info` / `task-details` divs that TaskRow now owns. The `summary` and `description` props are derived from `job.short_description` and `job.description` (per task 3.1). Until backend exposes `description`, pass `description={job.short_description}` and TaskRow will simply repeat — the visual split is then a no-op but no errors.

- [ ] **Step 5: Delete dead CSS from `volunteering/+page.svelte`'s `<style>` block.**

Rules to remove (verify the list against the file first):
- `.call-section`, `.call-header`, `.call-title`, `.call-meta`
- `.task-list`, `.task-row`, `.task-check`, `.task-info`, `.task-name`, `.task-meta`, `.task-details`, `.detail-row`, `.expand-btn`, `.chevron`
- `.list-header-row`

Rules to KEEP for now:
- `.call-banner-*` (status banners — until extracted in phase 8)
- `.max-week-row` / `.week-pick` / `.week-pick-label` (the per-call control row — until extracted)
- `.assignment-*` (the My Assignments section — has its own task below)
- `.submit-btn`, `.success-banner`

Goal: page goes from 313 lines of `<style>` to <100.

- [ ] **Step 6: Run the e2e demo (this is the canonical regression test for this page).**

```bash
# in one shell
make dev
# in another, after stack is up
make test-e2e
```

Expected: pass.

- [ ] **Step 7: Manual smoke at each density.**

In the browser: open the avatar menu, switch density from standard → compact → large. Verify:
- compact: tasks collapse to flat borderless list, meta inline-right
- standard: cards with subtle gap, summary one-liner, time only in expanded detail
- large: each task is a floating card with shadow halo

- [ ] **Step 8: Mobile smoke.**

```bash
make test-mobile-smoke
```

- [ ] **Step 9: Commit.**

```bash
git add frontend/src/routes/volunteering/+page.svelte
git commit -m "ui: volunteering page on CallCard + TaskRow

Replaces inline call-section / task-row markup with the new shells.
Deletes ~200 lines of now-dead CSS; remaining rules cover the bits not
yet extracted (banners, max-week selector, assignments)."
```

### Task 3.3: Delete `ItemCard.svelte` (no remaining callers)

- [ ] **Step 1: Verify no consumers remain.**

```bash
grep -rn "ItemCard" frontend/src
```

Expected: empty.

- [ ] **Step 2: Delete + commit.**

```bash
git rm frontend/src/lib/components/ItemCard.svelte frontend/src/lib/components/ItemCard.test.ts
git commit -m "ui: remove ItemCard (superseded by TaskRow)

The padding bug (var(--card-padding-y) applied to all four sides) is
gone with it."
```

### Task 3.4: Phase 3 merge

```bash
make lint-fe && make test-frontend && make test-e2e
git checkout main
git merge --no-ff feat/ui-03-volunteering
git push origin main
git checkout -b feat/ui-04-assign
```

---

## Phase 4: Assign page  *(branch: `feat/ui-04-assign`)*

`volunteer-calls/[id]/assign/+page.svelte` has the largest custom `<style>` block (508 lines) because it embeds the `AssignmentSpreadsheet` component plus several modals plus a sidebar.

### Task 4.1: Inventory + plan

- [ ] **Step 1: Read the file and list CSS-block sections.**

```bash
grep -n "^  \." frontend/src/routes/volunteer-calls/[id]/assign/+page.svelte | head -40
```

- [ ] **Step 2: Decide per section.**

The expected sections (verify against file):
- Page header → swap for `<PageHeader>`.
- Sidebar / filters → restyle to use new tokens, keep markup.
- Spreadsheet → **do not touch** — `AssignmentSpreadsheet.svelte` is its own component, restyling it is deferred.
- Assignment-action modals (notify, undo) → adopt new `.card` + `.btn` styling, delete custom rules.
- Floating action bar → restyle with the new pill-button shape.

### Task 4.2: Apply

- [ ] **Step 1: Swap page header to `<PageHeader title="Assign" />` (or whatever the existing h1 reads).**

- [ ] **Step 2: For each custom CSS rule on the page, if its visual goal is now covered by the new tokens / `.btn` / `.card`, delete the rule and let the global styles take over. If the rule encodes layout (grid, flexbox positions), keep but adjust spacing values to the new `--sp-*` scale.**

- [ ] **Step 3: Verify the spreadsheet still works** — drag-select volunteers, assign, undo. Demo flow runs through this in `demo.spec.ts`.

```bash
make dev  # in one shell
make test-e2e   # in another
```

- [ ] **Step 4: Commit.**

```bash
git add frontend/src/routes/volunteer-calls/[id]/assign/+page.svelte
git commit -m "ui: assign page on new shells (spreadsheet untouched)"
git checkout main
git merge --no-ff feat/ui-04-assign
git push origin main
git checkout -b feat/ui-05-people
```

**Out of scope for this phase:** `AssignmentSpreadsheet.svelte` itself. It needs its own design conversation; flag in `todo.md` if not already there.

---

## Phase 5: People  *(branch: `feat/ui-05-people`)*

### Task 5.1: People list (`/people`)

**Files:** Modify `frontend/src/routes/people/+page.svelte`.

- [ ] **Step 1: Swap page header to `<PageHeader>` with right-side meta carrying the role-filter count + pagination summary.**

- [ ] **Step 2: People rows currently use a custom card pattern; restyle so each row uses a soft-modular hairline divider rather than a per-row border.** Concretely, wrap the list in a `<div class="people-list">` with a top/bottom border, and rows separated by `border-top: 1px solid var(--hairline)` only.

- [ ] **Step 3: Delete every `.btn`-styling override in the local `<style>` block** (the global `.btn` now handles all of these).

- [ ] **Step 4: Search input + role filter Select should already inherit the right look from phase 2's component refresh — verify visually.**

- [ ] **Step 5: Test.**

```bash
pnpm exec vitest run src/routes/people  # whatever tests exist
make dev  # interactive: open /people, try search, change role filter, paginate
```

- [ ] **Step 6: Commit.**

```bash
git add frontend/src/routes/people/+page.svelte
git commit -m "ui: people list on soft-modular shells"
```

### Task 5.2: People detail (`/people/[id]`)

**Files:** Modify `frontend/src/routes/people/[id]/+page.svelte`.

- [ ] **Step 1: Wrap each editor section (notification prefs, calendar list, programs) in a `<div class="card">` and let global card styling carry the look.**

- [ ] **Step 2: Delete the custom card / panel rules in the local style block.**

- [ ] **Step 3: Commit + merge phase 5.**

```bash
git add frontend/src/routes/people/[id]/+page.svelte
git commit -m "ui: people detail on .card"
make lint-fe && make test-frontend
git checkout main
git merge --no-ff feat/ui-05-people
git push origin main
git checkout -b feat/ui-06-calls
```

---

## Phase 6: Volunteer-calls list + detail  *(branch: `feat/ui-06-calls`)*

### Task 6.1: Calls list (`/volunteer-calls`)

**Files:** Modify `frontend/src/routes/volunteer-calls/+page.svelte`.

- [ ] **Step 1: Swap page header. Each call in the list becomes a `<CallCard>` (head only — no controls or body, since this is the index page). Pass the status badge as `meta`.**

If `CallCard` doesn't support a "header-only" shape, allow `body` to be optional in the component and skip the bottom border when absent — small follow-up edit on `CallCard.svelte` in this branch is fine.

- [ ] **Step 2: Delete custom call-card CSS in the local style block.**

- [ ] **Step 3: Commit.**

```bash
git add frontend/src/routes/volunteer-calls/+page.svelte frontend/src/lib/components/CallCard.svelte
git commit -m "ui: calls list using CallCard (header-only shape supported)"
```

### Task 6.2: Call detail (`/volunteer-calls/[id]`)

**Files:** Modify `frontend/src/routes/volunteer-calls/[id]/+page.svelte`.

- [ ] **Step 1: Wrap the detail body in `<CallCard title={call.title}>{...}</CallCard>`. Leave `<TaskEditorRow>` instances in place** — they're admin-editor components (renamed from the original `TaskRow.svelte` during phase 2.3) and the call detail's actual functionality depends on their TaskEntryForm-embedded edit/delete API. The presentational `<TaskRow>` shell is not a substitute.

- [ ] **Step 2: Restyle `TaskEditorRow.svelte` to inherit the soft-modular look — same surface colors, hairlines, density vars — but keep its existing admin API unchanged.** This is a cosmetic pass on the editor row, not a swap.

- [ ] **Step 3: Delete dead CSS in the page-level `<style>` block.**

- [ ] **Step 4: Commit + merge phase 6.**

```bash
git add frontend/src/routes/volunteer-calls/[id]/+page.svelte frontend/src/lib/components/TaskEditorRow.svelte
git commit -m "ui: call detail on CallCard; TaskEditorRow restyled"
make lint-fe && make test-frontend && make test-e2e
git checkout main
git merge --no-ff feat/ui-06-calls
git push origin main
git checkout -b feat/ui-07-light-pages
```

---

## Phase 7: Light pages sweep  *(branch: `feat/ui-07-light-pages`)*

Pages with <100 lines of custom CSS. Mostly delete-and-let-globals-work.

For each of the following, do one commit per page with this pattern:

1. Swap any `<h1>` for `<PageHeader title="…" />`.
2. Delete every `.btn` / `.card` / `.badge` / form override in the local `<style>` block.
3. Verify the page renders correctly at standard density; spot-check compact + large.
4. `git add <file>; git commit -m "ui: <page> sweep"`.

### Task 7.1: `/settings`

**Files:** `frontend/src/routes/settings/+page.svelte`.
- Check whether the page-level density picker is still useful given the AvatarMenu picker. **Decision:** remove the page-level one — the avatar menu is the single source of truth.

### Task 7.2: `/profile`

**Files:** `frontend/src/routes/profile/+page.svelte` (174 lines — slightly heavier than the others but still primarily delete-overrides).

### Task 7.3: `/login`

**Files:** `frontend/src/routes/login/+page.svelte` (97 lines).
- Centered card layout — apply the new `.card` style + new button. Keep the welcome copy.

### Task 7.4: `/inbox`

**Files:** `frontend/src/routes/inbox/+page.svelte` (53 lines).
- Each inbox row is a candidate for a "lightweight TaskRow" pattern. If the alignment is awkward, fall back to a `.card` list.

### Task 7.5: `/reports`

**Files:** `frontend/src/routes/reports/+page.svelte` (43 lines).
- Wrap each summary stat in `<div class="summary-stat">` (already styled globally; verify the global `.summary-stat` rules survived phase 1 — if not, restore them).

### Task 7.6: `/verify`

**Files:** `frontend/src/routes/verify/+page.svelte` (39 lines).
- Centered status card. Trivial.

### Task 7.7: Phase 7 merge.

```bash
make lint-fe && make test-frontend
git checkout main
git merge --no-ff feat/ui-07-light-pages
git push origin main
git checkout -b feat/ui-08-density-audit
```

---

## Phase 8: Density audit + alias cleanup  *(branch: `feat/ui-08-density-audit`)*

Two cross-cutting concerns to close out.

### Task 8.1: Find components that ignore the density vars

**Files:** any `.svelte` whose `<style>` block uses hardcoded `px` / `rem` for paddings, font-sizes, button heights, etc., instead of the density tokens.

- [ ] **Step 1: Hunt.**

```bash
grep -rEn "padding:\s*[0-9]+(px|rem)" frontend/src --include="*.svelte" | grep -v "var(--" | head
grep -rEn "font-size:\s*[0-9]+(px|rem)" frontend/src --include="*.svelte" | grep -v "var(--" | head
grep -rEn "min-height:\s*[0-9]+(px|rem)" frontend/src --include="*.svelte" | grep -v "var(--"
```

- [ ] **Step 2: Convert each finding to the appropriate density var.**

Mapping cheat sheet (already in `app.css`):
- spacing → `--sp-2` through `--sp-6`
- font size → `--fz-body`, `--font-size-sm`, `--font-size-xs`
- button heights → `--btn-h`, `--btn-pad-x`
- card padding → `--card-pad-y`, `--card-pad-x`
- task / list row padding → `--task-pad-y`, `--task-pad-x`
- check / icon sizes → `--check-size`
- radius → `--radius`, `--radius-sm`

For each commit, name the component: `ui: density vars in <component>`.

- [ ] **Step 3: Verify the structural deltas land.** Open `/volunteering` in three browser windows side by side at compact / standard / large. The visual change between tiers must be obviously different at a glance — not just font scaling.

### Task 8.2: Remove legacy CSS aliases

**Files:** Modify `frontend/src/app.css` — delete the "Legacy density aliases" comment block and the variables it introduces (`--font-size-body`, `--spacing-*`, `--card-padding-*`, `--item-*`, `--btn-min-height`, etc.).

- [ ] **Step 1: Grep for each alias to confirm no remaining users.**

```bash
for alias in --font-size-body --spacing-md --card-padding-y --item-radius --btn-min-height --table-cell-padding; do
  echo "=== $alias ==="
  grep -rn "$alias" frontend/src --include="*.svelte" --include="*.css" | grep -v "app.css"
done
```

Each should return nothing. If any returns hits, those components are stragglers — convert them (task 8.1 missed them) before deleting.

- [ ] **Step 2: Delete the alias block in `app.css`, including the matching aliases in both `[data-density="compact"]` and `[data-density="large"]`.**

- [ ] **Step 3: Full smoke.**

```bash
make lint-fe && make test-frontend && make test-e2e && make test-mobile-smoke
make dev  # interactive sweep of every route at every density
```

- [ ] **Step 4: Commit + final merge.**

```bash
git add frontend/src/app.css
git commit -m "ui: drop legacy density aliases now that every component reads the new tokens"
git checkout main
git merge --no-ff feat/ui-08-density-audit
git push origin main
```

---

## Final verification (post-merge of all 8 branches)

- [ ] **Step 1: End-to-end demo.**

```bash
make dev
make demo  # headed, manual stepping — verifies the canonical user journey
```

- [ ] **Step 2: Coverage report.**

```bash
make test-frontend
# Confirm coverage ≥85% line & branch on the new PageHeader / CallCard / TaskRow components.
```

- [ ] **Step 3: Mobile smoke.**

```bash
make test-mobile-smoke
```

- [ ] **Step 4: Tag a release for deploy.** (Optional — only if the user wants this in prod immediately.)

```bash
# Pick the next tag — check existing tags first.
git tag v0.X.Y
git push --tags
# GitHub Actions takes it from here per .github/workflows/deploy.yml.
```

---

## Spec-coverage checklist (self-review of this plan)

- [x] "Prettier, more modern look" — covered by phase 1 tokens + classes (60% of the look) and phase 2 shells (the remaining 40%).
- [x] "Density toggle should be a more complete information-density transformation" — TaskRow's `[data-density=*]` rules structurally restructure (compact = flat list, large = floating cards). Token deltas widened in phase 1.3.
- [x] "Volunteer response cards should have less default whitespace" — standard density tightened in phase 1.3 (`--card-pad-y: 14px` was 1.25rem ≈ 20px; `--task-pad-y: 12px` similar reduction). Mobile retained via the `@media (max-width: 768px)` rules already in `app.css`.
- [x] "Multi-line descriptions, collapsed summary, expanded full text, no time duplication" — TaskRow (task 2.3) carries `.summary` (ellipsis-clamped) and `.description` (`white-space: pre-line`); time omitted from `.task-meta`, present only in `.task-detail`.
- [x] Mobile preserved — the new tokens and TaskRow respect the existing 768px breakpoint; `test-mobile-smoke` runs at every phase boundary.
- [x] Three pages requested for mockups (volunteering, density toggle, assignment-task) all covered: volunteering = phase 3; density toggle UI = AvatarMenu (phase 2.5); assignment+task = phase 4 (`/assign`) + phase 6.2 (call detail).
- [x] "Don't introduce significant functional changes" — explicitly out of scope (Withdraw, Save draft); flagged in the locked-in decisions and in `todo.md` Deferred.
- [x] "Apply to all pages, since not modular enough" — phases 3–7 cover every page with custom CSS.
