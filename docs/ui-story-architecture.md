# AstraOS UX story architecture

Phase 10A step 2. What each surface must communicate. Styling comes after.

## LIVE

**Question:** How does AstraOS decide what the merchant should offer?

```
BUYER INTENT
    ↓
QUALIFICATION
    ↓
PRODUCT MATCH
    ↓
PRODUCT → OFFER EXPANSION
    ↓
COMMERCIAL OPTIMISATION
    ↓
SELECTED COMPLETE OFFER
    ↓
NEGOTIATION
    ↓
TRANSACTION
```

Thesis: **Product ≠ Offer.** Product ranking identifies fit.
Offer optimisation identifies the merchant response. Show the inequality
only when the SKUs actually differ.

Stage questions:

| Stage | Question |
| --- | --- |
| Understand | What did AstraOS understand? |
| Qualify | What is actually eligible? |
| Match | Which product fits the buyer best? |
| Construct | How did products become commercial offers? |
| Optimise | Which complete offer should the merchant send? |
| Negotiate | How do the agents negotiate? |
| Transact | Did AstraOS safely execute the agreement? |

Default density: summary first, reasoning second, evidence on demand.

## ARENA

**Question:** Why is AstraOS better than simpler merchant strategies?

Same buyer, catalogue, inventory, policy, and buyer model.
Only the strategy changes.

Order: Default → Always Discount → Semantic Only → AstraOS.

The signature comparison is **Semantic Only vs AstraOS**: product
match plus standard terms versus whole-offer optimisation.

Results are a **synthetic** simulated-utility evaluation, not observed
sales uplift. Keep that visible.

## LEARN

**Question:** How can AstraOS improve once real outcomes exist?

```
INTENT → OFFER → OUTCOME → LEARNING RECORD
    → RESPONSE MODEL → FUTURE DECISION SUPPORT
```

Honesty: deterministic eligibility and real semantic matching are
active. Transparent buyer utility is primary. Learned response models
are experimental. Real observed response models are future.

## Merchant Data

**Question:** What merchant truth is available to AstraOS?

Dense operational catalogue: products, variants, stock, evidence
coverage, ingestion runs. Not a merchandising grid.

## Merchant Rules

**Question:** What commercial boundaries and objective govern AstraOS?

Compact groups: commercial objective (Growth / Balanced / Margin),
economics (margin floor, max discount), fulfilment, commercial options.
Objective selects among policy-safe Pareto offers. It does not rewrite
policy.
