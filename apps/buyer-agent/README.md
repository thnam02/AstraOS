# External Buyer Agent

Independent process. It is **not** AstraOS.

It talks only to the public machine interface:

```
GET  /api/v1/agent/capabilities
POST /api/v1/agent/offers/request
GET  /api/v1/agent/offers/{proposal_id}
POST /api/v1/agent/offers/counter
POST /api/v1/agent/offers/accept
GET  /api/v1/agent/orders/{ref}
GET  /api/v1/agent/transactions/{transaction_id}
```

It must not import `app.services`, `app.decision`, repositories, or models.

```bash
# from repo root, with AstraOS API running
cd apps/buyer-agent
python -m buyer_agent run --scenario urgent-traveller --mode deterministic
python -m buyer_agent run --scenario urgent-traveller --mode llm
python -m buyer_agent eval --mode deterministic
```

Or `make buyer-demo` / `make buyer-demo-deterministic`.
