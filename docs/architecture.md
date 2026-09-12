# AstraOS architecture

```
Buyer Agent
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
Pareto Optimisation
    ↓
Negotiation
    ↓
Transaction
```

Merchant systems / data sit below this stack: catalogue, inventory,
delivery capacity, warranty/bundle/returns, evidence, and merchant policy.

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
