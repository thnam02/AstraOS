# AstraOS reliability matrix

Phase 12 inventory of current behavior. Status is from inspected
code and targeted tests, not assumed earlier prompts.

| ID | Subsystem | Failure / Attack | Expected | Current | Status | Test | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Intent / LLM | Timeout / 500 / malformed / empty extraction | Rule fallback, explicit metadata | `parser_requested/used`, `fallback_used/reason` including `empty_extraction` | PASS | `test_llm_parser.py`, `test_phase12_hardening.py` | HTTP 500 → `provider_unavailable`; empty LLM constraints → `empty_extraction` |
| A2 | Intent / LLM | Prompt injection | Policy unchanged; no A$1 offer | Injection flagged; policy immutable | PASS | `test_llm_parser.py`, `test_phase12_hardening.py` | None |
| A3 | Intent | Contradictory constraints | Surfaced, not silently resolved | Ambiguity `contradictory_constraints` | PASS | `test_llm_parser.py` | None |
| B1 | Semantics | Model missing / load fail | Hashing fallback or ready degrade | Hashing fallback + `/ready` degraded | PASS | `test_semantic_provider.py` | None |
| B2 | Semantics | Stale / partial / dim mismatch | `/ready` reports mismatch; no mixed vectors | Degraded flags; required=false | PASS | `test_semantic_retrieval.py` | None |
| C1 | Qualification | Price / ANC / delivery violation | Not eligible; not in top-K | Evaluator rejects; match ranks eligible only | PASS | `test_eligibility.py`, `test_phase12_hardening.py` | None |
| D1 | Optimisation | Empty / single Pareto | No crash, no fake winner | Handles empty; single-offer select | PASS | `test_pareto.py`, `test_optimisation_api.py` | None |
| E1 | Policy | Buyer/LLM/agent override | Blocked | No agent policy mutation; injection ignored | PASS | `test_negotiation_safety.py`, `test_objective_security.py` | None |
| E2 | Objective | Extreme custom weights | Policy-safe only | Custom 1.0/0.0 still filters policy | PASS | `test_phase12_hardening.py` | None |
| F1 | Negotiation | Downward price erosion | NO SAFE COUNTER / limit; policy intact | Turns bounded; policy unchanged | PASS | `test_phase12_hardening.py` | None |
| F2 | Negotiation | Max turns / invalid transition | Explicit terminal / 409 | State machine + limit | PASS | `test_negotiation_state.py`, `test_negotiation_safety.py` | None |
| G1 | Transaction | Expired proposal accept | Fail; no order | `PROPOSAL_EXPIRED` | PASS | `test_transaction_api.py` | None |
| G2 | Transaction | Price / stock / delivery / policy change | Revalidate; fail if current truth fails | Failure codes recorded | PASS | `test_transaction_api.py`, `test_agent_protocol.py` | None |
| G3 | Transaction | Duplicate accept | Same order | Idempotency key + proposal confirmed | PASS | `test_transaction_api.py` | None |
| G4 | Transaction | Same key, different payload | Return first transaction | Current semantics | PASS | `test_phase12_hardening.py` | Documented, not redesigned |
| H1 | Inventory | Last-unit concurrent accept | One success, inventory ≥ 0 | `SELECT FOR UPDATE` | PASS | `test_inventory_reservation.py` | None |
| I1 | Agent protocol | Mutate policy/catalogue | 404/405 | No mutation routes | PASS | `test_ingestion_api.py`, `test_objective_security.py` | None |
| I2 | Agent protocol | Proof privacy | No COGS / margin / objective | Filtered public proof | PASS | `test_agent_privacy.py`, `test_phase12_hardening.py` | None |
| I3 | Buyer Agent | Malicious merchant text | Treated as data | Prompt boundaries + validator | PASS | `apps/buyer-agent/tests/test_injection.py` | None |
| J1 | Evidence | Unsupported claim | Not displayed as verified | Proof compiler filters | PASS | `test_proof.py`, `test_agent_proof.py` | None |
| K1 | Ingestion | Malformed / duplicate / negative | Validation fail; no silent corrupt apply | Validator + rollback | PASS | `test_ingestion_validation.py`, `test_ingestion_service.py` | None |
| K2 | Ingestion | Re-import / semantic refresh | Idempotent; inventory-only no re-embed | Fingerprint + selective reindex | PASS | `test_ingestion_service.py` | None |
| L1 | Arena | Strategy side effects | No stock/policy mutation | Snapshot, no transaction | PASS | `test_arena_fairness.py` | None |
| L2 | Arena | Unsafe offer selection | Not selectable | Validity gates | PASS | `test_arena_selection.py` | None |
| M1 | Frontend | Failure codes | Human labels, no stack traces | Failure codes humanized | PASS | `decisionNarrative.test.ts` | Labels added |
| N1 | Infra | `/health` vs `/ready` | Alive vs operational | Split endpoints | PASS | `test_health.py`, `test_agent_protocol.py` | None |
| O1 | Demo | Reset twice | Same clean policy/objective | `reset-state` + remigrate seed | PASS | `test_phase12_hardening.py`, `test_seed.py` | None |

## Safety invariants

1. No selected or executed offer may violate merchant policy.
2. Buyer text cannot set merchant commercial terms.
3. Transactions cannot create negative inventory.
4. The same accepted proposal does not create duplicate orders.
5. Proposals are revalidated before execution.
6. SATISFIED hard constraints require current merchant truth.
7. Public proof claims require evidence or transparent derivation.
8. External Buyer Agent cannot mutate policy, objective, or catalogue.
9. Stale or invalid proposals cannot silently transact.
10. Fallback mode is explicit (`fallback_used` / `fallback_reason`).
