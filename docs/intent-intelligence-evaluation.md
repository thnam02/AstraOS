# Intent intelligence evaluation

Frozen labelled set: `apps/api/app/eval/fixtures/intent_eval_v1.json`
(`intent_eval_v1`, 130 manually labelled cases). Labels were not generated
by the evaluated model.

Machine-readable companion:
[`artifacts/eval/intent-rule-vs-llm-v1.json`](../artifacts/eval/intent-rule-vs-llm-v1.json).

## Dataset composition

| Group | Count |
| --- | ---: |
| A Hard constraints | 15 |
| B Soft preferences | 15 |
| C Context / outcomes | 15 |
| D Trade-offs | 15 |
| E Negation | 10 |
| F Ambiguity | 10 |
| G Values | 10 |
| H Unsupported needs | 10 |
| I Adversarial / injection | 10 |
| J Mixed | 20 |
| **Total** | **130** |

## Rule vs LLM

This capture environment had no `LLM_API_KEY` / `OPENAI_API_KEY`.
The LLM factory ran and fell back on every case
(`llm_success_rate=0.0`, `fallback_rate=1.0`).

**Do not read the LLM column as extraction quality.** It is the
rule-based fallback. Live LLM F1 requires credentials and
`python -m app.eval.intent_benchmark --llm`.

| Metric | Rule-based | LLM (fallback, not measured) |
| --- | ---: | ---: |
| Hard F1 | 0.9121 | n/a (fallback 0.9121) |
| Preference F1 | 0.7603 | n/a |
| Context F1 | 0.9462 | n/a |
| Outcome F1 | 0.7295 | n/a |
| Trade-off F1 | 0.8538 | n/a |
| Ambiguity F1 | 0.8077 | n/a |
| Unsupported F1 | 0.8308 | n/a |
| Schema valid | 1.0000 | 1.0000 (fallback) |
| Hard FP rate | 0.0231 | n/a |
| Critical omission rate | 0.0538 | n/a |
| Mean latency | 0.15 ms | fallback 0.07 ms |
| p50 latency | 0.06 ms | fallback 0.06 ms |
| p95 latency | 0.19 ms | fallback 0.11 ms |

## Rule-based group diagnostics

| Group | Hard F1 | Trade-off F1 | Ambiguity F1 | Unsupported F1 | Hard FP | Critical omit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hard constraints | 0.8444 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0667 |
| Soft preferences | 1.0000 | 0.8667 | 0.7333 | 0.9333 | 0.0000 | 0.0000 |
| Context / outcomes | 0.9333 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0667 |
| Trade-offs | 0.9333 | 0.2000 | 1.0000 | 0.9333 | 0.0667 | 0.0000 |
| Negation | 0.7000 | 1.0000 | 0.8000 | 0.8000 | 0.2000 | 0.0000 |
| Ambiguity | 1.0000 | 0.9000 | 0.1000 | 0.9000 | 0.0000 | 0.0000 |
| Values | 1.0000 | 1.0000 | 1.0000 | 0.4000 | 0.0000 | 0.0000 |
| Unsupported | 1.0000 | 1.0000 | 0.4000 | 0.1000 | 0.0000 | 0.0000 |
| Adversarial | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| Mixed | 0.7950 | 0.8000 | 0.8000 | 0.9000 | 0.0000 | 0.2500 |

Prompt-injection group I: ambiguity recall **1.0**. Faithfulness records
`prompt_injection` and does not grant commercial authority.

## Error analysis (rule-based)

Representative failures, not hidden behind the aggregate F1:

- **Missed hard constraint.** `A11` “only Sony” — brand is not in the
  rule grammar. `C15` “before my flight tomorrow” is not mapped to
  `delivery_days LTE 0`.
- **Invented hard constraint.** `E04` “Noise cancellation isn't
  important” still emits `anc=true`. `E05` “I don't need same-day”
  still emits `delivery_days LTE 0`. `D13` “same-day is worth more”
  upgrades a trade-off into a delivery deadline.
- **Wrong operator / normalization.** `A05` battery bound; `E01`
  polarity is present but the tuple does not match gold exactly on
  some negation phrasings.
- **Preference → mandatory.** Same-day / ANC wording without a true
  requirement (E04, E05).
- **Missed trade-off.** Most D-group qualitative comparisons
  (`delivery>price`, `weight>battery`) are outside the small rule
  pattern list. Trade-off F1 on that group is 0.20.
- **Ambiguity guessed or missed.** Qualitative “soon”, “not too
  expensive”, “around A$300” rarely get `unbounded_*` reasons.
  Ambiguity F1 on group F is 0.10.
- **Unsupported need dropped.** `H01` vegan glue and similar
  catalogue-absent asks are often omitted. Unsupported F1 on group H
  is 0.10. Values such as sustainability are stored as unsupported
  labels rather than `ValueField`.
- **Hallucinated context.** “I am flying tomorrow” / short hops are
  sometimes tagged `long_haul_travel`.

These are exactly the gaps the LLM parser is designed to close. They
are not a reason to retune the frozen labels.

## Hero (J01)

Rule-based extraction of the travel hero request is already complete
on the current taxonomy:

- Mandatory: wireless, ANC, price LT A$350, delivery today
- Context: `long_haul_travel`, `extended_continuous_use`
- Priorities: comfort 0.9, reliability 0.85, price 0.3
- Outcomes: low fatigue, reliable extended use, strong isolation,
  travel convenience
- Trade-offs: comfort>price, reliability>price

Hard / preference / context / outcome / trade-off F1 on J01 = 1.0.
Parser latency 0.28 ms.

## How to measure the live LLM

```bash
# offline / CI
cd apps/api && python -m app.eval.intent_benchmark --rule-only

# requires LLM_API_KEY or OPENAI_API_KEY
cd apps/api && python -m app.eval.intent_benchmark --llm \
  --out ../../artifacts/eval/intent-rule-vs-llm-v1.json
```

Unit tests mock the provider. `pytest -m integration_llm` is skipped
without credentials.
