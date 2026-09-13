# AstraOS UI audit

Phase 10A step 1. Inspection only — no redesign in this document.
Inspected `apps/web` source, tokens, dependencies, and the Phase 10
storytelling report. Visual capture of LIVE / ARENA / LEARN at
1440×900 is required during later QA; this audit is from current code.

## Existing visual system

Tokens live in `apps/web/app/globals.css` `@theme`:

| Token | Value | Role |
| --- | --- | --- |
| `canvas` | `#f4f2ec` | App background (warm paper) |
| `surface` | `#ffffff` | Primary surface |
| `ink` | `#141413` | Foreground |
| `muted` | `#5c5a54` | Secondary text |
| `line` | `#dddad2` | Borders |
| `success` / `danger` / `warning` / `uncertain` | greens / reds / amber / blue | Semantic |
| `radius-control` | `6px` | Controls only |
| `shadow-panel` | 1px hairline | Minimal elevation |

Fonts: Inter (sans) + JetBrains Mono (metrics/IDs).

Component CSS classes: `.panel`, `.panel-decision`, `.eyebrow`,
`.btn-primary`, `.btn-ghost`, `.btn-quiet`, `.chip-soft`, `.control`,
`.table-dense`, `.surface-0/1/2`.

No purple gradients, glass cards, or giant KPI tiles. Header uses a
light `backdrop-blur` on `bg-surface/95` — the only glass-adjacent
treatment.

**Missing tokens:** secondary/raised surfaces, muted border, page/section
type scale, table density, chart series colors, informational state.
Spacing is ad hoc (`gap-3`, `gap-4`, `gap-6`, `space-y-4/5/6`).

## Existing component inventory

**App routes:** `/` LIVE, `/arena`, `/learn`, `/catalogue`,
`/catalogue/[productId]`. No Presentation / Demo / Judge / Pitch routes
or query params.

**Shared (`components/shared/`):** `AppHeader`, `PageContainer`,
`Panel`, `SectionHeader`, `Chip`, `DataBadge`, `StatusBadge` (API
connection only), `EvidenceBadge`, `ScoreBar`, `StatStrip`, `StatTile`,
`Disclosure`, `Drawer` (custom, not Radix), `EmptyState`, `ErrorState`,
`MerchantPolicyDrawer`.

**LIVE:** `LiveWorkbench`, `ProcessRail`, `IntentPanel`,
`QualificationInspect`, `MatchList`, `DecisionBridge`, `OfferExplorer`,
`OptimisationPanel`, `ParetoChart`, `RecommendedOffer`,
`NegotiationPanel`, `TransactionPanel`, `ApiStatus`.

**ARENA:** `ArenaWorkbench`, `StrategyCard`, `StrategyComparison`,
`BuyerDecision`, `BenchmarkView`, `ExperimentInspector`, `FitBar`.

**LEARN:** `LearnWorkbench`.

**Merchant Data:** `CatalogueExplorer`, `IngestionPanel`,
`ProductInspector`.

**Libs:** `decisionNarrative`, `arenaDisplay`, `matchDisplay`, `intent`,
`money`, `api`, `processRail` tests.

**Dependencies:** Next 16, React 19, Tailwind 4, Recharts 3,
Phosphor icons. **No shadcn. No Radix. No Motion/Framer. No 21st.**

**Icons:** Phosphor is a dependency; most UI is text marks (`✓ ● ○ !`)
rather than icons.

## Repeated patterns

- Eyebrow + title + muted supporting line
- `btn-primary` / `btn-ghost` / `btn-quiet`
- `StatStrip` count grids (Qualify, Construct, Optimise)
- Custom drawer for proof / inspect / rules
- Human labels via `arenaDisplay` / `decisionNarrative` / `matchDisplay`
- `formatAudCents` for money
- Process marks: complete / active / future / failed

## Duplicate components

- `Panel` vs `.panel` / `.panel-decision` vs raw `border border-line bg-surface`
- `Chip` vs `.chip-soft` vs `DataBadge` vs `EvidenceBadge`
- `StatusBadge` (connection) vs ad-hoc PASS/FAIL text
- `StatTile` / `StatRow` vs `StatStrip` vs hand-rolled `dl` grids
- Custom `Drawer` vs potential Sheet
- Arena `FitBar` vs shared `ScoreBar`
- Multiple empty/error treatments (`ErrorState` vs inline `text-danger`)

## Inconsistent patterns

- Header primary nav (LIVE / ARENA / LEARN) vs secondary (Merchant Data
  as link, Merchant Rules as drawer)
- LIVE empty state is a centered hero (`text-3xl`); running LIVE is a
  dense three-column workspace
- Some stages use `panel-decision`; others are unboxed
- Parser select appears twice (empty + running) with different option order
- Status color used without a consistent badge primitive
- Catalogue evidence quality is a bordered box; LIVE stats use `StatStrip`

## Typography issues

- Page titles mix `text-3xl` (empty LIVE), `text-xl` (loading), and
  `SectionHeader` defaults
- Selected offer price is `text-3xl` — the loudest number on LIVE
- Eyebrow is consistent (11px / 0.06em)
- Some operator strings still leak (`LT`, `LTE`) in compact intent chips
  when not AUD/days

## Spacing issues

- Page padding `px-6 py-6` is stable
- LIVE grid gaps `gap-6` vs inner `space-y-3/4`
- ProcessRail wraps with `gap-x-0.5`; connectors are literal `──`
- 1366×768: three-column grid only at `xl`; below that columns stack
  and the selected-offer rail is no longer sticky-dominant

## Color/status issues

- Semantic colors exist but are applied inconsistently
- `StatusBadge` only covers API connection
- Transaction / qualification statuses are text + color, not one badge
- Arena “WON” is green text; policy-blocked cards use warning border
- Status is mostly not color-only (marks + words), which is good

## Information hierarchy issues

Phase 10 already established summary → reasoning → inspect. Remaining:

- LIVE empty state still reads slightly like a landing page
- Technical IDs (SKU, run IDs) appear next to human titles
- Optimise can still feel like chart + many controls in one column
- Inspect drawers are consistent in mechanism, not in internal layout

## LIVE issues

- ProcessRail is compact (good) but still click-to-navigate; states
  COMPLETE / ACTIVE / UPCOMING / FAILED exist, not BLOCKED
- Left column is compact intent; center is the stage; right is selected
  offer — proportions match the brief (`~20 / 55 / 25`)
- Product → Offer bridge and Product ≠ Offer exist and use live data
- Qualification inspect exists; default view is counts
- Offer explorer is a dense table (good) with many filters
- Negotiation is structured (not chat), payload behind Inspect
- Transaction is an execution rail, not checkout

## Arena issues

- Controlled-experiment copy exists on the page header
- Strategy cards are consistent
- Semantic Only vs AstraOS comparison exists in `StrategyComparison`
- Benchmark table + business scatter exist
- Synthetic disclaimer exists in display helpers
- Visual system still uses raw borders rather than Astra primitives

## Learn issues

- Maturity copy lives in `LEARN_STATUS` / `LEARN_STORY`
- Page still mixes operational actions (generate/train) with narrative
- Chart is Recharts; tokens for series are not centralized
- `setState` in `useEffect` on load (existing eslint finding)

## Merchant Data issues

- Dense table + search + brand filter (good)
- Ingestion panel sits above the table
- Product inspector is a separate route, not a drawer
- Evidence quality is a compact `dl`, not a card grid

## Components worth preserving

- `ProcessRail` state machine (`processRailState`)
- `DecisionBridge` / `expansionSteps` (live numbers)
- `RecommendedOffer` proof drawer
- `NegotiationPanel` structured turns
- `TransactionPanel` revalidation rail
- `arenaDisplay` / `decisionNarrative` / `matchDisplay` label layer
- `formatAudCents`
- Empty / loading copy that avoids “AI is thinking”

## Components that should be refactored

- Shared primitives → `components/astra` (tokens, not one-off classes)
- `Drawer` → accessible Sheet/Dialog with focus trap
- `StatusBadge` → general status system
- `AppHeader` / `PageContainer` → shell tokens
- ProcessRail marks/connectors → tokenized process state
- Arena / Learn / Catalogue surfaces → consume Astra primitives
- Number/status formatters → one helper module

## Components that should be removed

- Duplicate unused exports if `StatTile` is unused after migration
- Inline panel clones once `AstraPanel` exists
- No Presentation Mode remnants found to delete

## UX problems vs visual problems

**UX (already mostly solved in Phase 10):** story order, Product ≠ Offer
only when true, inspect-on-demand, machine negotiation, honest Learn
maturity, no fake numbers.

**Visual (this phase):** no primitive layer, no shadcn, tokens incomplete,
duplicate badges/panels, drawer a11y, ProcessRail still slightly like
text nav, empty LIVE a bit hero-like, status system not unified,
chart colors not tokenized.
