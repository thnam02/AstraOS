# AstraOS architecture

```
Buyer Agent
    ↓
Agent Gateway   REST /api/v1/agent/*   optional MCP stdio
    ↓
Intent Intelligence
    ↓
Eligibility
    ↓
Semantic Matching
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
| LLM parser | Rule-based intent / negotiation interpreter |
| Embedding provider | Cached embeddings, then local hashing vectors |
| Learned model | Cold-start utility |
| MCP | REST `/api/v1/agent/*` |
