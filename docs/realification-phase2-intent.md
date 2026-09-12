# Phase 2 — Real Intent Intelligence

UNDERSTAND only. Matching embeddings, optimisation, Pareto, Arena, and
transaction logic were not changed. Phase 1 baseline artifacts were not
overwritten.

## Before

From [`docs/realification-baseline.md`](realification-baseline.md) and
[`artifacts/baseline/astraos-baseline-v1.json`](../artifacts/baseline/astraos-baseline-v1.json):

- Parser mode: `rule_based` / `rule_based.v2`
- Old 77-case retrieval eval extraction F1: constraints 0.9596,
  context 0.9048, prefs 0.8918, outcomes 0.5349
- Hero LIVE: Sonic Cabin 32 top match 0.8202; selected offer
  Aurora Commute 06 `AUR-T06-BLK` A$301.85, utility 0.876066
- Intent parse latency: 0.29 ms median
- Full decision latency: 1858.51 ms median
- No Phase 2 labelled intent set existed

## After

- Primary demo mode: `INTENT_PARSER_MODE=llm`
- Provider: OpenAI-compatible JSON client (`openai_compatible`)
- Default model: `gpt-4o-mini`
- Prompt: `intent-parser-v2`
- Extraction schema: `llm-extraction.v1` → `LLMIntentExtraction` →
  normalizer → faithfulness → `ShoppingIntent`
- Temperature: 0
- One bounded structured repair, then rule-based fallback
- CI / unit tests remain `INTENT_PARSER_MODE=rule_based`

Live LLM extraction was **not** scored in this environment (no API key).
Fallback behaviour was scored: 130/130 cases fell back with
`fallback_reason=provider_unconfigured`.

## Rule vs LLM

See [`docs/intent-intelligence-evaluation.md`](intent-intelligence-evaluation.md).

| Metric | Rule-based | Live LLM |
| --- | ---: | --- |
| Hard F1 | 0.9121 | not measured |
| Preference F1 | 0.7603 | not measured |
| Context F1 | 0.9462 | not measured |
| Outcome F1 | 0.7295 | not measured |
| Trade-off F1 | 0.8538 | not measured |
| Ambiguity F1 | 0.8077 | not measured |
| Unsupported F1 | 0.8308 | not measured |
| Schema valid | 1.0 | n/a (no live completions) |
| Latency | 0.15 ms mean | n/a; fallback ~0.07 ms |

Hybrid merge was **not** implemented. It should only be considered after
a live LLM run shows worse explicit-constraint recall than rules.

## Failure analysis

Rule-based gaps on the frozen 130-case set:

1. Brand constraints are absent from the grammar.
2. Negation sometimes inverts into a positive hard constraint.
3. Qualitative trade-offs are mostly missed (group D F1 0.20).
4. Ambiguity reasons are rarely emitted (group F F1 0.10).
5. Unsupported catalogue-absent needs are often dropped (group H F1 0.10).
6. Values such as sustainability are stored as unsupported labels,
   not `ValueField`.

These labels were not edited after seeing predictions.

## Fallback behavior

```
LLM parser
  ├── success → ShoppingIntent (parser_used=llm)
  └── failure → RuleBasedIntentParser
                parser_requested=llm
                parser_used=rule_based
                fallback_used=true
                fallback_reason=timeout|authentication|
                  provider_unconfigured|provider_unavailable|
                  validation_failed
```

`/ready` reports `intent_parser` with `requested_mode`,
`provider_configured`, and `fallback_available` without a live call.

## Safety tests

Mocked unit tests cover:

- schema failure + one repair success
- repair exhaustion → factory fallback
- timeout / unavailable → fallback
- soft language not upgraded to mandatory
- negation polarity
- contradictory price and brand constraints kept + flagged
- prompt injection recorded, no commercial authority
- unsupported needs and unbounded ambiguity retained
- source_phrase provenance and parser metadata / token usage

Live `integration_llm` tests are skipped without credentials.

## Hero scenario

Rule-based (and therefore current fallback) extraction of the Sydney →
Singapore hero request matches the required conceptual interpretation
on the current taxonomy. J01 field-level F1 is 1.0 for hard constraints,
preferences, context, outcomes, and trade-offs.

A live LLM hero parse still needs `LLM_API_KEY`.

## Remaining limitations

- No live LLM quality number in this capture.
- Rule-based brand / deep trade-off / ambiguity / unsupported coverage
  remains weak. That is expected and is why the LLM path exists.
- Word numbers such as “three hundred and fifty dollars” stay ambiguous
  unless a numeric form is present.
- Matching still uses hashing embeddings (`hashing-vectorizer-384`).

## Recommendation

**PHASE 3 — REAL SEMANTIC EMBEDDINGS** after a credentialed LLM
benchmark is recorded on the same `intent_eval_v1` set.

Do not begin Phase 3 until that live comparison exists if judge
questions will focus on parser accuracy.
