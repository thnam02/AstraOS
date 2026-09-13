# Phase 10A — Astra Design System + UX Refactor

## UI Audit

Completed first. See `docs/ui-audit.md`. No component work started until
the inventory existed.

## Story Architecture

See `docs/ui-story-architecture.md`.

- LIVE: how AstraOS decides the merchant offer
- ARENA: why AstraOS vs simpler strategies
- LEARN: how improvement works after real outcomes
- Merchant Data: what merchant truth is available
- Merchant Rules: policy + objective boundaries

## Design Principles

Summary first, reasoning second, evidence on demand. Enterprise decision
intelligence: dense, calm, precise. No Presentation / Demo / Judge /
Pitch mode. Backend remains source of truth.

Warm paper/ink identity from Phase 10 was kept. The ui-ux-pro-max
“Data-Dense Dashboard” style was used as quality reference; its blue
palette was **not** adopted.

## Tokens

`apps/web/app/globals.css`:

- Surfaces: `canvas`, `surface`, `surface-2`, `raised`
- Border: `line`, `line-muted`
- Foreground: `ink`, `muted`
- States: `success`, `warning`, `danger`, `info` / `uncertain`
- Charts: `chart-grid`, `chart-axis`, `chart-muted`, `chart-selected`
- Type: `type-page`, `type-section`, `type-card`, `type-body`,
  `type-small`, `type-metric`, `eyebrow`
- Radius 6px, one-pixel panel shadow
- shadcn CSS variables mapped onto Astra tokens

## shadcn Integration

Configured via `apps/web/components.json` (New York, CSS variables,
neutral mapped to Astra). Primitives added:

Button, Badge, Tabs, Tooltip, Sheet, Dialog, Table, Select, Separator,
ScrollArea, Skeleton, DropdownMenu.

`lib/utils.ts` uses `clsx` + `tailwind-merge`. Accidental npm `cn`
package from the CLI was removed. Feature pages should not import raw
shadcn except through Astra wrappers.

## Astra Components

`apps/web/components/astra/`:

Panel, SectionHeader, StageHeader, Metric, MetricRow, StatusBadge,
SourceBadge, Score, DataTable, Inspector, Empty/Error/LoadingState,
KeyValue, Timeline, Delta, Callout.

`components/shared/*` now re-exports these so existing LIVE/ARENA/LEARN
call sites picked up the system without a one-pass rewrite.

## Cursor UI Rules

`.cursor/rules/astra-ui.mdc` — 22 Astra UI rules, scoped to
`apps/web/**/*.{ts,tsx,css}`.

## 21st Usage

No 21st.dev MCP or tooling was available in this environment. Not
blocked. shadcn used as the primitive accelerator instead.

## Global Shell

Same primary nav (LIVE / ARENA / LEARN) and secondary (Merchant Data /
Merchant Rules). `TooltipProvider` wraps the app. Page titles use
`type-page`. Drawers use `AstraInspector` (Radix Sheet) for focus
management.

## ProcessRail

Still the LIVE backbone. States: complete / active / future / failed /
blocked. Compact text process, not pill navigation. Connector color
softens for upcoming stages. Motion is color-only and reduced-motion
safe.

## LIVE

Empty state title scaled to `type-page` (less landing-page). Loading
uses `AstraLoadingState` with pipeline copy. Stage domain components
preserved; they consume Astra primitives through shared wrappers.
Product → Offer bridge and Product ≠ Offer remain live-data only.

## Arena

Synthetic evaluation is an `AstraCallout`. Strategy cards and Semantic
Only vs AstraOS comparison unchanged in logic.

## Learn

`AstraSectionHeader`, maturity table with `AstraStatusBadge`, synthetic
callout. Experimental status stays honest.

## Merchant Data

Still a dense operational table. Status chips go through
`AstraStatusBadge`.

## Merchant Rules

Drawer migrated to `AstraInspector`. Groups remain: objective,
economics, fulfilment / options.

## Motion

No Framer Motion added. CSS `motion-safe` transitions on score bars
and ProcessRail. `prefers-reduced-motion` still globally respected.

## Responsive

Desktop-first. LIVE three-column grid at `xl`. Below that, columns
stack. 1440 and 1366 remain the QA targets.

## Accessibility

Inspector/Rules use Radix Sheet (focus trap, close control, title).
Status badges include a screen-reader tone prefix. Focus rings
unchanged. Status is never color-only.

## Performance

No virtualization added. Offer explorer already filters. Chart
libraries unchanged.

## Removed Legacy UI

Custom overlay Drawer replaced. Duplicate empty/error/panel/stat
implementations now wrap Astra. No Presentation Mode existed to
remove. Phosphor remains unused as a primary icon set; shadcn uses
Lucide internally.

## Targeted Validation

Frontend unit tests (narrative, arena display, process rail, match
display). One production `next build`. **Full backend pytest was not
run.**

## Remaining UX Issues

- LIVE stage bodies are incrementally tokenized, not fully rewritten
- 1366 stacked layout still taller than ideal
- Two pre-existing eslint `set-state-in-effect` findings (Learn,
  Merchant Rules) were not redesigned
- Catalogue product inspector is still a route, not a drawer
- 21st.dev not connected
