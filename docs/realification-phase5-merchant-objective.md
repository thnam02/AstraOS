# Phase 5 — Configurable Merchant Objective

Phase 5 makes the final Pareto selection a backend-owned merchant
commercial objective. Policy still defines what is allowed. Objective
only chooses among policy-safe efficient offers. Phase 1–4 artifacts
were not overwritten.

## Previous Selection Logic

Confirmed in `apps/api/app/decision/optimisation/selection.py`:

- Rule: `normalized_weighted_sum`
- `DEFAULT_ALPHA = 0.5` (buyer-utility weight)
- `score = alpha * norm(utility) + (1 - alpha) * norm(contribution)`
- Alpha was a request field / constant, not persisted merchant config
- Utility is a 0..1 cold-start score
- Contribution is integer cents and may be negative
- Zero range: `normalize` returns `1.0` (no divide-by-zero)
- Tie-break: higher score, higher contribution, higher utility, lower
  intervention cost, SKU, offer ID

That formula was mathematically valid and is reused. The commercial
problem was: “Why 50/50?” had no merchant answer.

## New Objective Architecture

```
candidate offers
    ↓
merchant economics
    ↓
policy safety          ← hard guardrails (unchanged)
    ↓
simulated buyer utility
    ↓
Pareto frontier        ← unchanged by strategy
    ↓
MERCHANT OBJECTIVE     ← Growth / Balanced / Margin / Custom
    ↓
selected merchant response
```

`MerchantObjective` is a separate concept from `MerchantPolicy`.

## Policy vs Objective

**Policy** answers what is allowed: minimum margin, max discount,
subsidy authority, stock, returns.

**Objective** answers what is preferred among allowed efficient offers:
buyer-fit weight vs contribution weight.

Objective never overrides policy. Switching Growth / Balanced / Margin
does not rebuild eligibility, matching, construction, economics, utility,
or the frontier.

## Presets

| Mode | Buyer weight | Merchant weight |
| --- | ---: | ---: |
| GROWTH | 0.70 | 0.30 |
| BALANCED | 0.50 | 0.50 |
| MARGIN | 0.30 | 0.70 |
| CUSTOM | validated, then normalised to sum 1 | |

Default is **BALANCED**, which preserves the old α = 0.5 behaviour.

Weights must be finite and ≥ 0. Preset weights are fixed and were not
tuned against Arena.

## Selection Formula

```
score_i =
    w_buyer * normalized_buyer_utility_i
  + w_merchant * normalized_contribution_i
```

Select the highest-scored Pareto offer. Intervention cost remains
explanatory / secondary.

Tie-break (stable, not row order):

1. higher weighted score
2. higher contribution
3. higher buyer utility
4. lower intervention cost
5. SKU
6. offer ID

## Frontier Invariance

For the same intent, catalogue, inventory, policy, and utility model,
Growth / Balanced / Margin produce the **same Pareto frontier**.

Frozen eval: `frontier_invariant_status = true` on all 5 missions.

Lightweight reselection (`POST /api/v1/optimisation/runs/{id}/reselect`)
reuses stored frontier points. Mean latency **6.5 ms**. No LLM call,
embedding inference, or offer reconstruction.

## Hero Scenario

Hero intent + `URGENT_TRAVELLER`. Frontier size 36 in all three modes.

| Objective | Product | Utility | Contribution | Score |
| --- | --- | ---: | ---: | ---: |
| GROWTH | Atlas Cabin 72 | 0.871 | A$100.64 | 0.776 |
| BALANCED | Atlas Cabin 72 | 0.868 | A$102.64 | 0.723 |
| MARGIN | Aurora Commute 06 | 0.832 | A$124.15 | 0.771 |

Growth and Balanced keep Atlas Cabin 72 (different efficient
configurations). Margin selects Aurora Commute 06 and preserves more
contribution. Both offers are Pareto-efficient. This is not instability.

## Objective Sensitivity

Five frozen missions: Urgent Traveller, Budget, Assurance, Quality,
Balanced. All five were objective-sensitive.

| Pair | Missions that change | Avg Δ utility | Avg Δ contribution |
| --- | ---: | ---: | ---: |
| Growth → Balanced | 80% | −0.056 | +A$31.65 |
| Balanced → Margin | 100% | −0.049 | +A$18.59 |
| Growth → Margin | 100% | −0.105 | +A$50.24 |

Merchant objective materially changes the selected trade-off.

## Arena Analysis

Default Arena benchmarks snapshot **BALANCED**. Same seed + same
objective is reproducible. Baseline strategies are unaffected.

Optional ASTRAOS-only experiment (8 synthetic missions, seed 2026):

| Mode | Selection rate | Contrib / opportunity | Avg utility | No-offer | Policy violations |
| --- | ---: | ---: | ---: | ---: | ---: |
| GROWTH | 1.00 | A$88.50 | 0.759 | 0 | 0 |
| BALANCED | 1.00 | A$186.68 | 0.708 | 0 | 0 |
| MARGIN | 0.875 | A$209.11 | 0.633 | 0 | 0 |

Synthetic disclaimer applies. Weights were not tuned to win Arena.

## API

Merchant-owned:

- `GET /api/v1/merchant/objective`
- `PATCH /api/v1/merchant/objective`
- `POST /api/v1/optimisation/runs/{id}/reselect`

Payload examples:

```json
{ "mode": "MARGIN" }
```

```json
{ "mode": "CUSTOM", "buyer_weight": 0.4, "merchant_weight": 0.6 }
```

`OptimisationResponse` adds `merchant_objective`, `selection` metadata,
and `objective_comparisons`. Existing clients keep working.

`/api/v1/agent/*` cannot set or read merchant weights. Public proposals
do not leak mode, weights, or strategy copy.

## UI

Merchant Rules drawer: compact **Commercial Objective** presets.
LIVE Optimise shows current weights, the same frontier, and a moving
selected point. Technical inspector exposes mode, weights, version,
normalized components, and final score.

## Performance

Reselection mean 6.5 ms (max 8.9 ms) over 15 reselects. Full decision
is only required when policy, catalogue, or intent changes.

## Tests

- Domain: presets, CUSTOM normalisation, negative/NaN rejection,
  persist, default migration, run snapshot, frontier invariance,
  expected selection change, insensitive dominance, single-point
  frontier, zero-range, stable tie-break
- Security: buyer/agent cannot PATCH objective; public proposal does
  not leak weights; prompt injection cannot change objective
- Negotiation: snapshot at session creation; later live change does
  not rewrite the session; accepted proposals stay immutable
- Arena: snapshot, reproducibility, baselines unaffected

## Limitations

- Single-merchant hackathon setup
- CUSTOM is API-capable; the drawer emphasises the three presets
- Arena objective experiment is small and synthetic
- Negotiation snapshots objective at session creation, not live
- Historical hero LIVE path used `INTENT_ADAPTED`; this eval used
  `URGENT_TRAVELLER` on the same hero text

## Recommendation

Phase 6 — Merchant Data Ingestion.

Do not begin Phase 6 automatically.
