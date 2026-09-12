# Judge Q&A

**Where does buyer utility come from?**
A transparent, manually specified cold-start function over product fit,
price, delivery, warranty, bundle, and returns. Weights adapt to the
structured intent. It is Simulated Buyer Utility, not learned from sales.

**Is this real conversion probability?**
No. Arena and LEARN use synthetic buyer-agent outcomes. The learned score
is a Synthetic Response Score.

**Why Pareto?**
Many policy-safe offers are dominated. AstraOS keeps the efficient
trade-offs between simulated buyer utility and merchant contribution,
then picks one with a declared rule.

**Why not just discount?**
Discount is one lever. Same-day, warranty, bundle, and returns can be
cheaper for the merchant and better for the intent. Policy still binds.

**Does the LLM set prices?**
No. The LLM only interprets buyer language into a typed ShoppingIntent.
Pricing, policy, economics and offer selection are deterministic AstraOS
services.

**What happens if the LLM is unavailable?**
AstraOS automatically falls back to the deterministic rule parser.
`/ready` reports `requested_mode`, `provider_configured`, and
`fallback_available` without making a live model call.

**How do you know the parser is accurate?**
AstraOS evaluates it against a frozen manually labelled intent benchmark
(`intent_eval_v1`) and reports field-level precision/recall/F1 plus
critical hard-constraint false positives and omissions.

**Can prompt injection bypass merchant policy?**
No. Buyer text never has authority over policy or commercial execution.
Injection attempts are recorded as ambiguities. Eligibility, pricing, and
selection remain deterministic.

**Why use an LLM?**
Language interpretation only. Commercial terms are applied by
deterministic services. Demo default is `INTENT_PARSER_MODE=llm` with
rule-based fallback. CI stays offline.

**What if the LLM hallucinates?**
Unsupported fields are rejected. Soft language is demoted. Eligibility
still uses hard constraints. Timeouts and validation failures fall back
to the rule-based parser.

**How do you stop unsafe discounts?**
Merchant policy (margin floor, max discount, subsidies). Prompt injection
cannot change policy or invent stock.

**Where does product evidence come from?**
Seeded merchant specifications and provenance records. Semantic match
reasons cite those facts. Unsupported claims are not invented.

**How does the transaction work?**
Accept a proposal id. Revalidate live price, inventory, delivery, and
policy. Reserve, then write an immutable local order. No payment moves.

**Is the Buyer Agent your product?**
No. It is an external client. AstraOS is the merchant-side engine.

**How would this integrate with a real retailer?**
The agent adapter maps onto the same canonical services. A retailer OMS
and payment stack would replace the local reservation/order snapshot.

**How does AstraOS learn over time?**
Intent → Offer → Outcome records. Today those labels are synthetic.
Later, real B2A outcomes can replace them. No online bandit.

**Why is this different from semantic search?**
Search ranks products. AstraOS constructs and selects commercial offers
under policy.

**Why is this different from a pricing engine?**
Price is one dimension. Delivery, warranty, bundle, and returns are
first-class.

**Why is this different from a chatbot?**
The merchant response is a machine-readable proposal with proof, expiry,
and allowed actions — not a paragraph of sales copy.
