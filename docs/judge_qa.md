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
then picks one with the merchant's configured commercial objective.

**Why did you use a 50/50 optimisation?**
We no longer assume every merchant has the same objective. Balanced is
the default, but merchants can select Growth or Margin-oriented
strategies. All operate over the same Pareto-efficient frontier.

**Can the merchant sacrifice margin completely to win the buyer?**
No. Hard merchant policy is enforced before objective selection.

**Does Growth just mean discounting more?**
No. AstraOS optimises the complete offer vector including delivery,
warranty, bundles, returns and price.

**Does changing strategy rerun the entire AI pipeline?**
The underlying efficient frontier is unchanged. AstraOS can reselect
from the frontier using the new merchant objective when the underlying
commercial state has not changed.

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

**Is the Buyer Agent just part of your UI?**
No. It runs as an independent process in `apps/buyer-agent` and
communicates only through the public AstraOS agent protocol.

**Does the Buyer Agent know merchant margins?**
No. Merchant economics remain private to AstraOS. The public proposal
exposes customer price, delivery, warranty, bundle, returns, proof, and
allowed actions.

**Can the buyer tell AstraOS what price to charge?**
The buyer can request a maximum acceptable price, but AstraOS determines
whether any merchant-safe proposal can satisfy it.

**Do you support agent protocols?**
AstraOS exposes a protocol-neutral REST machine interface
(`astraos-agent` v1.0) and an optional MCP adapter over the same
merchant logic. REST is the guaranteed demo path.

**What happens when the buyer accepts?**
AstraOS revalidates the immutable proposal against current merchant
state, reserves inventory and creates the order through the commerce
execution boundary. The buyer submits a proposal id, not commercial
terms.

**How would this integrate with a real retailer?**
The agent adapter maps onto the same canonical services. A retailer OMS
and payment stack would replace the local reservation/order snapshot.

**How does AstraOS learn over time?**
Intent → Offer → Outcome records. Today those labels are synthetic.
Later, real B2A outcomes can replace them. No online bandit.

**Is this keyword search?**
No. Eligible products are represented using semantic embeddings generated
from merchant-supported product facts. Buyer context and desired outcomes
are embedded into the same space and retrieved semantically. Hard
constraints are applied first, then a grounded reranker explains Product
Fit, Context Fit, Preference Fit, and Evidence Coverage.

**Can semantic similarity override price or delivery constraints?**
No. Mandatory constraints are evaluated deterministically before any
semantic retrieval. A perfect travel embedding cannot resurrect a SKU
that violates budget or same-day delivery.

**Do embeddings invent product claims?**
No. Product semantic documents are constructed only from merchant
catalogue facts and evidence. The model does not write marketing copy.

**What happens if the embedding model is unavailable?**
AstraOS has a hashing fallback so the commerce pipeline remains
operational. Match metadata records `provider_requested`,
`provider_used`, and `fallback_reason`. The system does not pretend
neural retrieval occurred.

**How did you validate matching?**
Against a frozen manually-labelled retrieval set using Recall@K, MRR and
NDCG, with hard-constraint violation rate measured separately. Hashing
and the sentence-transformer are compared with and without the same
grounded reranker.

**Why is this different from semantic search?**
Search ranks products. AstraOS constructs and selects commercial offers
under policy. Semantic retrieval is only the MATCH stage, and only over
already-eligible SKUs.

**Why is this different from a pricing engine?**
Price is one dimension. Delivery, warranty, bundle, and returns are
first-class.

**Why is this different from a chatbot?**
The merchant response is a machine-readable proposal with proof, expiry,
and allowed actions — not a paragraph of sales copy.

**Is your catalogue hardcoded?**
No. AstraOS ships with a deterministic demo merchant for reproducibility,
but the decision engine operates on a canonical merchant model populated
through the ingestion layer. We support versioned JSON and CSV merchant
feeds.

**How would a retailer connect AstraOS?**
Their PIM/ERP/OMS or commerce platform maps into the ingestion adapter.
The downstream decision engine remains unchanged.

**What happens when merchant data changes?**
AstraOS upserts changed records and selectively refreshes semantic
embeddings only when semantic product facts change.

**Do you invent missing product attributes?**
No. Missing data remains unknown and can block mandatory buyer
requirements.

**Can the buyer agent upload merchant data?**
No. Merchant ingestion is a separate merchant-side administrative
boundary.
