# Phase 11 — Arena Ablation & Competitive Proof

## Purpose

Phase 11 does not add intelligence. It proves, under a controlled
synthetic Arena, what incremental merchant value each capability
contributes.

The question is:

> Why does a merchant need AstraOS instead of semantic search or
> discounting?

The competition story, measured rather than asserted:

**Semantic search finds a product. AstraOS builds a commercial
response.**

Buyer selection uses a transparent **simulated buyer utility**. Results
are not observed real-world sales uplift.

## Experimental Controls

Every strategy in one mission receives the same:

- ShoppingIntent
- qualified catalogue / inventory / delivery snapshot
- merchant policy
- product evidence state
- buyer utility model and outside option (`0.42`)
- seed `2026`
- BALANCED merchant objective (primary run)

Only the strategy differs. Strategies read an immutable
`ArenaContext`. They do not reserve stock, mutate policy, or persist
negotiation state. Invalid or policy-unsafe offers never enter buyer
selection.

## Strategies

Strategy versions stored with the benchmark: `DEFAULT v1`,
`ALWAYS_DISCOUNT v1`, `SEMANTIC_ONLY v1`, `ASTRAOS v1`.
`CHEAPEST_ELIGIBLE v1` remains registered for extended benchmarks.

### Default

Highest-ranked eligible product (`top_match_variant`) plus that
product's conceptual default terms: BASE price, STANDARD delivery,
STANDARD_12 warranty, no bundle, STANDARD_30 returns. No Pareto.

**Honesty:** Default already uses semantic ranking. It was not silently
changed. `BASELINE_DEFAULT` was not introduced. Default → Semantic Only
does **not** isolate semantic search.

### Always Discount

Same top semantic product. Maximum policy-safe DISCOUNT on default
dimensions. No Pareto.

### Semantic Only

Eligible products → semantic ranking → top match → default commercial
configuration → policy validation → buyer evaluation. Standalone
implementation. Never reads `recommended_offer_id`. No Pareto, no
warranty/bundle/returns/delivery search.

Because Default already ranks semantically, Semantic Only and Default
produced identical offers in this run.

### AstraOS

Live pipeline: semantic match → offer construction → economics →
policy → buyer utility → Pareto → merchant-objective selection.
`used_pareto=True`. Same information as baselines.

## Benchmark Configuration

| Field | Value |
| --- | --- |
| Seed | `2026` |
| Missions | `100` |
| Strategies | DEFAULT, ALWAYS_DISCOUNT, SEMANTIC_ONLY, ASTRAOS |
| Buyer model | `simulated.v1` (cold-start; not the learned response model) |
| Utility version | `simulated.v1` |
| Arena version | `arena.v2` |
| Strategy set | `strategies.v2` |
| Merchant objective | BALANCED (`buyer_weight=0.5`, `merchant_weight=0.5`) |
| Policy | `policy.v1`, min margin `0.15`, max discount `0.10` |
| Outside option | `0.42` |
| Segment shares | budget 20%, urgent 20%, assurance 15%, quality 15%, balanced 15%, gaming_studio 10%, difficult 5% |
| Catalogue | seeded headphones snapshot (`inventory_fingerprint` in artifact) |
| Runtime | 140.1 s wall; 86.0 s in-runner (`860 ms` / mission) |

Secondary objective experiment: 20 missions, seed 2026, ASTRAOS only,
GROWTH / BALANCED / MARGIN.

## Overall Results

Synthetic selection among the four ablation strategies. Contribution
per opportunity is the merchant KPI.

| Strategy | Selection | Contribution / opp. | Buyer utility | Intervention cost | No offer | Policy violations | Hard-constraint fails |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default | 0.0% | A$0.00 | 0.564 | A$0.00 | 0.0% | 0.0% | 33.0% |
| Always Discount | 4.0% | A$3.02 | 0.579 | A$37.34 | 0.0% | 0.0% | 33.0% |
| Semantic Only | 0.0% | A$0.00 | 0.564 | A$0.00 | 0.0% | 0.0% | 33.0% |
| AstraOS | 96.0% | A$183.46 | 0.705 | A$27.21 | 0.0% | 0.0% | 0.0% |

Default / Discount / Semantic Only fail hard constraints on 33% of
missions (typically same-day delivery). Those offers are not selectable.
AstraOS produced a policy-safe, constraint-safe offer on every mission.

No-purchase rate: **0.0**. AstraOS always cleared the `0.42` outside
option. That is a measured outcome, not a forced winner.

In this synthetic benchmark, AstraOS achieved higher contribution per
opportunity than Semantic Only. That is not a real-world revenue claim.

## Incremental Ablation

### Default → Discount

| Metric | Delta |
| --- | ---: |
| Selection rate | +0.04 |
| Contribution / opportunity | +A$3.02 |
| Buyer utility | +0.015 |
| Intervention cost | +A$37.34 |

Discounting buys a small amount of simulated utility at high merchant
cost. It wins only when price is the deciding lever.

### Default → Semantic

| Metric | Delta |
| --- | ---: |
| Selection rate | 0 |
| Contribution / opportunity | 0 |
| Buyer utility | 0 |
| Intervention cost | 0 |

Expected. Default already uses the same semantic top match and the same
default terms. This stage does **not** isolate semantic search.

### Semantic → AstraOS

| Metric | Delta |
| --- | ---: |
| Selection rate | +0.96 |
| Contribution / opportunity | +A$183.46 |
| Buyer utility | +0.141 |
| Intervention cost | +A$27.21 |

This is the valid offer-optimisation ablation. AstraOS spends less
average intervention cost than Always Discount while producing much
higher simulated utility and contribution per opportunity.

## AstraOS vs Semantic Only

Denominator: missions where both produced valid (policy-safe,
constraint-safe) offers. **67 / 100**.

| Outcome | Count | Share of both-valid |
| --- | ---: | ---: |
| AstraOS preferred | 67 | 100% |
| Semantic preferred | 0 | 0% |
| Tie | 0 | 0% |
| Neither / outside option | 0 | 0% |

When AstraOS was preferred:

- average contribution delta: **+A$45.32**
- average utility delta: **+0.117**

All 67 both-valid differences were classified `MULTIPLE` (more than one
commercial field changed). On the other 33 missions Semantic Only was
not selectable (hard-constraint failure); AstraOS still produced a
valid offer.

## Intervention Attribution

Among the 67 missions where AstraOS was preferred over a valid
Semantic Only offer, levers that actually differed:

| Lever | Share |
| --- | ---: |
| Price | 100% |
| Delivery | 100% |
| Warranty | 100% |
| Returns | 80.6% |
| Product | 89.6% |
| Bundle | 0% |
| Multi-lever | 100% |

Derived from offer outputs only. Every AstraOS-over-Semantic win used
more than one lever.

## Segment Analysis

Primary segments (selection / contribution per opportunity / utility /
intervention cost):

| Segment | n | Default | Discount | Semantic | AstraOS |
| --- | ---: | --- | --- | --- | --- |
| Budget | 20 | 0% / A$0 / 0.542 / A$0 | 0% / A$0 / 0.571 / A$26.84 | 0% / A$0 / 0.542 / A$0 | **100% / A$73.38 / 0.716 / A$23.75** |
| Urgent | 20 | 0% / A$0 / 0.541 / A$0 | 0% / A$0 / 0.549 / A$33.23 | 0% / A$0 / 0.541 / A$0 | **100% / A$238.88 / 0.757 / A$29.50** |
| Assurance | 15 | 0% / A$0 / 0.552 / A$0 | 0% / A$0 / 0.559 / A$33.13 | 0% / A$0 / 0.552 / A$0 | **100% / A$204.86 / 0.677 / A$27.00** |
| Quality | 15 | 0% / A$0 / 0.548 / A$0 | 0% / A$0 / 0.557 / A$44.46 | 0% / A$0 / 0.548 / A$0 | **100% / A$251.81 / 0.656 / A$27.00** |
| Balanced | 15 | 0% / A$0 / 0.609 / A$0 | 0% / A$0 / 0.624 / A$38.66 | 0% / A$0 / 0.609 / A$0 | **100% / A$215.14 / 0.642 / A$27.00** |
| Gaming / studio | 10 | 0% / A$0 / 0.666 / A$0 | **40% / A$30.19 / 0.689 / A$56.32** | 0% / A$0 / 0.666 / A$0 | 60% / A$111.97 / 0.766 / A$27.00 |

AstraOS did **not** win every segment. Always Discount won 4 of 10
gaming/studio missions. That is the credible loss mode: a price-first
response on a product the buyer already liked beat a richer, more
expensive AstraOS configuration.

## Pairwise Results

Buyer prefers row over column when both are valid. Denominator:
`both_valid_offers` (67 missions except as noted).

|  | Default | Discount | Semantic | AstraOS |
| --- | ---: | ---: | ---: | ---: |
| Default | — | 0% | 0% (100% tie) | 0% |
| Discount | 100% | — | 100% | 6.0% |
| Semantic | 0% (100% tie) | 0% | — | 0% |
| AstraOS | 100% | 94.0% | 100% | — |

Default vs Semantic Only is a complete tie. That confirms they are the
same strategy in this codebase.

## Merchant Objective Sensitivity

ASTRAOS only. Same 20 missions, seed 2026, same catalogue / policy /
buyer model.

| Mode | Selection | Contribution / opp. | Buyer utility | Intervention cost |
| --- | ---: | ---: | ---: | ---: |
| GROWTH | 100% | A$76.78 | 0.775 | A$35.89 |
| BALANCED | 100% | A$191.07 | 0.714 | A$27.00 |
| MARGIN | 90% | A$216.59 | 0.643 | A$26.80 |

Growth buys more simulated utility at lower contribution. Margin
preserves more contribution and loses 10% of simulated selections
(outside option). This is sensitivity analysis, not the primary
ablation.

## Example Missions

Real missions from the seed-2026 / 100-mission run. Not constructed.

### Urgent — `m-2026-0039`

“Long-haul flight tonight… delivered today.”

| | Default / Semantic Only | Always Discount | AstraOS |
| --- | --- | --- | --- |
| Product | Verve Travel Pro 45 | same | Nimbus Travel Pro 97 |
| Price | A$350.11 | A$315.10 | A$498.69 |
| Delivery | Standard (2d) | Standard (2d) | Same-day |
| Warranty | 12m | 12m | 36m |
| Status | Hard-constraint fail | Hard-constraint fail | Valid |
| Utility | 0.580 | 0.589 | **0.796** |
| Contribution | A$96.25 | A$61.24 | **A$255.04** |

Baselines cannot satisfy same-day. AstraOS can. Selected: AstraOS.

### Budget — `m-2026-0010`

Default/Semantic: Echo Travel Pro 85 at A$266.04, utility 0.469.
Discount: same product at A$239.44, utility 0.505, cost A$26.60.
AstraOS: Echo Lite 80 at A$124.33, same-day + 36m warranty, utility
0.705, cost A$22.00. Selected: AstraOS. Discount spent more to buy
less simulated utility.

### Assurance — `m-2026-0046`

Semantic Only: Sonic Cabin 32 (WHT), standard terms, A$310.06,
utility 0.583.
AstraOS: Sonic Cabin 32 (BLK), same-day, 36m warranty, flex returns,
utility 0.645, contribution A$204.86 vs A$99.78.

### Balanced — `m-2026-0084`

Same family (Zenith Signature 148). AstraOS changes colour/config,
adds same-day, 36m warranty, flex returns. Utility 0.634 → 0.699.
Contribution A$125.62 → A$230.56.

## Where AstraOS Wins

96 missions. Deterministic categories (no LLM):

- `HIGHER_PRODUCT_FIT` — 89
- `FASTER_DELIVERY` — 7

Hero **product ≠ offer** mission (`m-2026-0066`, quality):

```
SEMANTIC ONLY          ASTRAOS
Orion Ultra 109        Orion Ultra 109
ORI-P109-SLV           ORI-P109-SLV
A$604.38               A$643.38
Standard delivery      SAME-DAY
12m warranty           36M WARRANTY
Standard returns       FLEX_60
utility 0.519          utility 0.659
contrib  A$239.81      contrib  A$251.81
```

Same product. Non-price levers (delivery, warranty, returns). Higher
simulated utility **and** higher contribution than both Semantic Only
and Always Discount (which spent A$60.44 to reach utility 0.532).

Urgent missions are the other strong case: baselines fail same-day
hard constraints; AstraOS constructs a feasible offer.

## Where AstraOS Loses

4 missions, all `DISCOUNT_BETTER_VALUE`, all gaming/studio
(`INTENT_ADAPTED`). Example `m-2026-0094`:

| | Semantic / Default | Always Discount | AstraOS |
| --- | --- | --- | --- |
| Product | Zenith Signature 148 | same | Pulse Pro 122 |
| Price | A$501.38 | **A$451.24** | A$618.32 |
| Delivery | Standard | Standard | Same-day |
| Warranty | 12m | 12m | 36m |
| Utility | 0.691 | **0.712** | 0.705 |
| Contribution | A$125.62 | A$75.48 | A$308.88 |

The simulated buyer preferred a cheaper version of the semantic
product over AstraOS's richer, more expensive substitute. AstraOS
preserved more contribution but lost the mission. That is the
correct “why not always AstraOS” answer.

## Synthetic Evaluation Limitations

- Buyer choice is a transparent weighted utility, not purchase or
  conversion probability.
- Catalogue, missions, and policy are seeded / synthetic.
- Default and Semantic Only are currently the same strategy, so this
  run cannot isolate semantic-search value.
- 96% AstraOS selection is a property of this mission mix, hard
  constraints, and offer space — not a real-world win rate.
- The benchmark was not used to retrain a response model.
- Language such as “increases retailer revenue by X% in the real
  world” is not supported.

## Targeted Validation

Full backend `pytest` was **not** run.

Targeted Arena tests (33 passed):

```
pytest tests/test_arena_ablation.py
pytest tests/test_arena_strategies.py
pytest tests/test_arena_metrics.py
pytest tests/test_arena_selection.py
pytest tests/test_arena_missions.py
pytest tests/test_arena_api.py
pytest tests/test_objective_arena.py
pytest tests/test_arena_fairness.py
```

Lint / frontend:

```
ruff check apps/api/app/decision/arena apps/api/app/eval/arena_ablation.py
          apps/api/app/services/arena.py apps/api/app/schemas/arena.py
          apps/api/tests/test_arena_ablation.py
          apps/api/tests/test_arena_strategies.py
          apps/api/tests/test_arena_metrics.py
          apps/api/tests/test_objective_arena.py
npx tsx --test lib/arenaDisplay.test.ts
npx tsc --noEmit
```

Targeted mypy was skipped (would traverse the API package). Deferred
to Phase 12.

Intent parsing, semantic model, qualification, buyer utility,
economics, Pareto dominance, merchant policy, and transaction logic
were not tuned to improve Arena results.

## Recommendation

**PHASE 10 — FINAL UI/UX STORYTELLING**

Do not begin the next phase automatically.
