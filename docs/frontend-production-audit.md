# AstraOS Frontend Production Audit

**Scope:** `apps/web`  
**Date:** 2026-09-13  
**Stack:** Next.js 16 · React 19 · Tailwind 4 · Radix/shadcn · Recharts · Phosphor

This audit precedes the production hardening pass. No Presentation / Demo / Judge / Pitch mode exists (forbidden by Astra UI rules). Demo mutation controls inside Transact are operational recovery hooks, not a product mode.

---

## Executive summary

LIVE is the strongest surface (stage shells, DecisionWorkflow, narrative helpers, evidence drawers). ARENA, LEARN, and Merchant Data lag: raw enums, ad-hoc tables, incomplete loading/empty/error states, and uneven Astra adoption.

**Highest leverage:**

1. Delete orphan DecisionHome stack and unused shared exports  
2. Enforce format helpers + humanized enums  
3. Harden Catalogue / LEARN states and tables  
4. Token hygiene (ban hex, standardize radius)  
5. Unify rail node primitives; keep ProcessRail types + DecisionWorkflow interactive  

---

## Routes

| Path | Surface |
|------|---------|
| `/` | LIVE (`LiveWorkbench`) |
| `/arena` | ARENA |
| `/learn` | LEARN |
| `/catalogue` | Merchant Data |
| `/catalogue/[productId]` | Product inspector |

No route-level `loading.tsx` / `error.tsx` / `not-found.tsx`.

---

## Design tokens (`app/globals.css`)

Present: canvas/surface/ink/muted/line/mark/semantic colors; type scale; radius-control 6px; spacing; panel/stage-result.

Gaps: arbitrary `rounded-[6px]`, hex chart colors, one-off `text-[8px]`–`text-[15px]`, opacity hacks without named tokens.

---

## Astra + shared inventory

**Astra:** Panel, SectionHeader, Empty/Error/Loading, Inspector, DataTable, Status/Source badges, Metric, Score, KeyValue, Callout, Delta, Timeline, LiveStatus.

**Shared wrappers:** Drawer→Inspector, Panel, Empty/Error, SectionHeader, badges, StatStrip. Several unused: Chip, Panel (call sites), ScoreBar, StatTile/StatRow.

**Orphans (not mounted):** `DecisionHome`, `DecisionSummary`, `SelectedOfferSummary`, `OfferOptimisationSummary`, `BuyerRequestSummary`, `ApiStatus`.

---

## Surface findings

### LIVE

- Strong StageResult / StageSection grouping after recent pass  
- Dual button systems (shadcn vs `btn-primary`)  
- DecisionWorkflow duplicates StageNode vs ProcessRail  
- Inspect drawers still expose raw JSON (acceptable behind Inspect)  
- Utility often `.toFixed(2)` instead of `formatUtility`  
- OfferExplorer needs full-space vs filtered-view clarity + sticky header  

### ARENA

- Good controlled-experiment framing potential; charts use hardcoded hex  
- ExperimentInspector is JSON-heavy  
- Strategy cards need consistent schema display  

### LEARN

- Reads like ML console: raw `ACTIVE`/`EXPERIMENTAL`, algorithm keys  
- Missing loading skeleton; empty tables without CTA  
- Chart hex colors  

### Merchant Data (Catalogue)

- Dense table OK; no loading/empty row; unlabeled search  
- `limit: 200` client-side only  
- ProductInspector: raw attribute keys, `"null"` strings, raw codes  

### Merchant Rules

- AstraInspector + form structure good  
- `rounded-full` toggles violate radius rule  
- Toggle a11y incomplete (`aria-pressed` without switch role)  
- No loading while policy fetches  

### Evidence / Technical Inspector

- Match evidence strong; other inspectors default to JSON  
- Prefer KeyValue first, raw JSON behind disclosure  

---

## Severity heatmap

| Area | Severity |
|------|----------|
| Dead DecisionHome stack | High |
| LEARN/Catalogue states + enums | High |
| Format helper non-adoption | High |
| ProcessRail / DecisionWorkflow duplication | Medium |
| Chart hardcoding | Medium |
| Merchant Rules toggle radius/a11y | Medium |
| Dual button/icon systems | Medium |
| Missing Next error/loading routes | Low–Med |

---

## Hardening order (this pass)

1. Tokens + shell consistency  
2. Shared rail node + page width rhythm  
3. Remove dead UI  
4. LIVE Construct explorer + remaining LIVE polish  
5. Arena / Learn / Catalogue / Rules  
6. Tables / forms / drawers / states  
7. A11y / responsive / performance  
8. Frontend lint, typecheck, tests, production build  

**Constraint:** No business/scoring logic changes. No Presentation Mode. Targeted frontend checks only until final validation.

---

## Pass status (completed)

Hardening pass executed against this audit. Validation:

- `npm run lint` — 0 errors (1 pre-existing `LiveWorkbench` exhaustive-deps warning)
- `npx tsc --noEmit` — pass
- `npm test` — 61/61 pass
- `npm run build` — pass (Next.js 16.3.5)

No Presentation/Demo mode added. No intentional business/scoring logic changes.

