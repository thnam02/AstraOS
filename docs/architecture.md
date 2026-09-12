# AstraOS architecture

```
┌─────────────────────┐
│ External Buyer Agent│  apps/buyer-agent  (independent process)
│ deterministic | LLM │
└──────────┬──────────┘
           │ REST / MCP
           ▼
┌─────────────────────┐
│ AstraOS Agent API   │  /api/v1/agent/*
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Merchant Decision   │
│ Engine              │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Transaction Boundary│
└─────────────────────┘
```

The Buyer Agent is not AstraOS. It is an external evaluator/client.
It must not import merchant services, repositories, models, or policy.

```
EXTERNAL BUYER AGENT
    ↓
Agent Gateway   REST /api/v1/agent/*   optional MCP stdio
    ↓
Intent Intelligence
    Natural language → structured LLM extraction → schema validation
    → canonical normalisation → faithfulness checks → ShoppingIntent
    ↓
Eligibility
    ↓
Semantic Matching
    IntentSemanticProfile + ProductSemanticDocument
    → local sentence-transformer (hashing fallback)
    → cosine over eligible variants only
    → grounded deterministic rerank
    ↓
Offer Construction
    ↓
Merchant Economics / Policy
    ↓
Policy-safe offers
    ↓
Buyer Utility
    ↓
Pareto Frontier
    ↓
Merchant Objective
    ↓
Recommended Offer
    ↓
Negotiation
    ↓
Transaction
```

Merchant **policy** is a hard guardrail: what is allowed. Merchant
**objective** is a soft preference among policy-safe Pareto offers:
Growth (70/30), Balanced (50/50 default), or Margin (30/70). Objective
never overrides policy, and never rebuilds the frontier.

Merchant systems / data sit below this stack: catalogue, inventory,
delivery capacity, warranty/bundle/returns, evidence, and merchant policy.

```
PIM / ERP / OMS / CSV / JSON
          ↓
Merchant Ingestion Layer
          ↓
Canonical Commerce Model
          ↓
AstraOS Decision Engine
```

Phase 6 implements versioned JSON and CSV adapters. Shopify/SAP
connectors are not implemented; they would plug into the same adapter
boundary. Downstream services do not branch on whether a row came from
the demo seed or an import.

Demo default: `INTENT_PARSER_MODE=llm` (`intent-parser-v2`,
`llm-extraction.v1`). The LLM never receives COGS, catalogue candidates,
Pareto results, or merchant policy. Commercial authority stays in the
deterministic services. Offline / CI mode remains `rule_based`.

## Protocol layer

The agent adapter translates protocol messages onto existing services.
It does not price, qualify, match, optimise, or rewrite policy.

```
EXTERNAL BUYER AGENT
        │
        ├── REST (guaranteed)
        └── MCP  (optional; calls REST)
        ▼
AgentGatewayService
        ▼
NegotiationService / TransactionService / DecisionService
```

## Learning loop

```
Intent → Offer → Buyer/agent response → Outcome
      → CommerceInteraction → dataset → response model
      → shadow / experimental score
```

Default optimisation still uses cold-start Simulated Buyer Utility.
The learned score is experimental and trained on synthetic Arena labels.

## Fallback

| Dependency | If unavailable |
| --- | --- |
| LLM parser | Structured extraction with one repair, then rule-based fallback |
| Embedding provider | Local `BAAI/bge-small-en-v1.5` over eligible products; hashing fallback if the model is unavailable |
| Learned model | Cold-start utility |
| MCP | REST `/api/v1/agent/*` |
