"use client";

import { useEffect, useState, type ReactNode } from "react";

import { ApiStatus } from "@/components/live/ApiStatus";
import { NegotiationPanel } from "@/components/live/NegotiationPanel";
import { OfferExplorer } from "@/components/live/OfferExplorer";
import { OptimisationPanel } from "@/components/live/OptimisationPanel";
import { TransactionPanel } from "@/components/live/TransactionPanel";
import {
  acceptProposal,
  createNegotiation,
  getNegotiation,
  postNegotiationTurn,
  runOptimisation,
  setDemoDeliveryCapacity,
  setDemoInventory,
  setDemoPolicy,
  simulateNegotiationBuyer,
} from "@/lib/api";
import { HERO_INTENT, contextLabel, fieldLabel } from "@/lib/intent";
import { formatAudCents } from "@/lib/money";
import type {
  BuyerProfile,
  GenerateOffersResponse,
  MatchResponse,
  AcceptProposalResponse,
  NegotiationResponse,
  OptimisationResponse,
  RankedProductMatch,
  ShoppingIntent,
} from "@/types";

function processState(
  hasMatch: boolean,
  hasOffers: boolean,
  hasOpt: boolean,
  hasNego: boolean,
  hasTxn: boolean,
  txnComplete: boolean,
  id: string,
): string {
  if (!hasMatch) return "not started";
  if (id === "understand" || id === "qualify" || id === "match") return "complete";
  if (id === "construct") return hasOffers ? "complete" : "not started";
  if (id === "optimise") {
    if (hasOpt) return "complete";
    return hasOffers ? "next" : "not started";
  }
  if (id === "negotiate") {
    if (hasTxn || hasNego) return "complete";
    return hasOpt ? "next" : "locked";
  }
  if (id === "transact") {
    if (txnComplete) return "complete";
    if (hasTxn) return "active";
    return hasNego ? "next" : "locked";
  }
  return "locked";
}

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function importanceLabel(value: number): string {
  if (value >= 0.75) return "HIGH";
  if (value <= 0.25) return "LOW";
  return "MEDIUM";
}

export function LiveWorkbench() {
  const [text, setText] = useState(HERO_INTENT);
  const [parserMode, setParserMode] = useState<"rule_based" | "llm">("rule_based");
  const [profile, setProfile] = useState<BuyerProfile>("INTENT_ADAPTED");
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [offers, setOffers] = useState<GenerateOffersResponse | null>(null);
  const [optimisation, setOptimisation] = useState<OptimisationResponse | null>(
    null,
  );
  const [negotiation, setNegotiation] = useState<NegotiationResponse | null>(
    null,
  );
  const [transaction, setTransaction] = useState<AcceptProposalResponse | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function executeAcceptance(session: NegotiationResponse) {
    if (!session.proposal) return;
    const result = await acceptProposal(session.session_id, {
      proposal_id: session.proposal.proposal_id,
      idempotency_key:
        globalThis.crypto?.randomUUID?.() ?? `web-${Date.now()}`,
    });
    setTransaction(result);
    setNegotiation(await getNegotiation(session.session_id));
  }

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const decided = await createNegotiation({
        intent: text,
        parser_mode: parserMode,
        buyer_profile: profile,
        max_products: 8,
      });
      if (decided.match) setResult(decided.match);
      if (decided.construction) setOffers(decided.construction);
      if (decided.optimisation) setOptimisation(decided.optimisation);
      setNegotiation(decided);
      setTransaction(null);
    } catch {
      setError("Negotiation failed. Is the API running?");
    } finally {
      setBusy(false);
    }
  }

  async function rerunOptimisation(nextProfile: BuyerProfile) {
    if (!offers) return;
    setProfile(nextProfile);
    setBusy(true);
    setError(null);
    try {
      setOptimisation(
        await runOptimisation({
          offer_run_id: offers.offer_run_id,
          buyer_profile: nextProfile,
        }),
      );
    } catch {
      setError("Optimisation failed.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    function onPolicy() {
      if (!offers) return;
      void rerunOptimisation(profile);
    }
    window.addEventListener("astraos:policy-changed", onPolicy);
    return () => window.removeEventListener("astraos:policy-changed", onPolicy);
  }, [offers, profile]);

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(260px,0.9fr)_minmax(380px,1.2fr)_minmax(280px,1fr)]">
      <section className="panel space-y-5">
        <div className="space-y-2">
          <p className="eyebrow">Buyer Agent request</p>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            Deep intent intake
          </h1>
          <p className="text-sm leading-6 text-muted">
            Language is interpreted. Hard rules decide who may compete.
            Semantic fit ranks eligible products. Construction enumerates
            configurations. Optimisation then keeps only policy-safe Pareto
            trade-offs.
          </p>
        </div>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={11}
          className="control w-full resize-y px-3 py-3 text-sm leading-6"
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setText(HERO_INTENT)}
            className="cursor-pointer text-xs font-medium tracking-[0.08em] text-muted hover:text-ink"
          >
            Example request
          </button>
          <span className="text-xs text-muted">
            Parser: {parserMode === "rule_based" ? "Rule-based" : "LLM"}
          </span>
          <select
            value={parserMode}
            onChange={(event) =>
              setParserMode(event.target.value as "rule_based" | "llm")
            }
            className="control px-2 py-1 text-xs"
          >
            <option value="rule_based">Rule-based</option>
            <option value="llm">LLM</option>
          </select>
        </div>
        <button
          type="button"
          onClick={() => void run()}
          disabled={busy || !text.trim()}
          className="btn-primary"
        >
          {busy ? "NEGOTIATING…" : "UNDERSTAND → NEGOTIATE"}
        </button>
        {busy ? (
          <p className="text-sm text-muted">
            Understanding intent, checking mandatory requirements, matching the
            catalogue, constructing offers, applying merchant policy, and
            computing the efficient frontier.
          </p>
        ) : null}
        {error ? <p className="text-sm text-danger">{error}</p> : null}
        <ApiStatus />
      </section>

      <section className="panel space-y-5">
        <div>
          <p className="eyebrow">AstraOS understanding</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            Qualify, match, construct
          </h2>
        </div>
        {!result ? (
          <p className="text-sm leading-6 text-muted">
            Submit a request to see structured intent, hard qualification, and
            grounded semantic matches.
          </p>
        ) : (
          <>
            <DeepIntent intent={result.intent} />
            <div className="border border-line bg-canvas px-4 py-4 text-sm">
              <p className="eyebrow">Qualification</p>
              <p className="mt-2 tabular-nums">
                {result.qualification.variants_checked} checked ·{" "}
                {result.qualification.eligible} eligible ·{" "}
                {result.qualification.violated} violated ·{" "}
                {result.qualification.uncertain} uncertain
              </p>
              <p className="mt-2 text-xs text-muted">
                Semantic ranking runs only on eligible SKUs. Fit is not a
                purchase probability.
              </p>
            </div>
          </>
        )}
      </section>

      <aside className="panel space-y-5">
        <div>
          <p className="eyebrow">Best product matches</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            Semantic fit
          </h2>
        </div>
        {result ? (
          <div className="space-y-3">
            {result.semantic_matching.matches.map((match) => (
              <MatchCard key={match.variant_id} match={match} />
            ))}
            {result.semantic_matching.matches.length === 0 ? (
              <p className="text-sm text-muted">
                No eligible products to rank.
              </p>
            ) : null}
            <p className="text-xs text-muted">
              {result.timing.total_ms.toFixed(0)} ms · parse{" "}
              {result.timing.intent_parse_ms.toFixed(0)} · qualify{" "}
              {result.timing.qualification_ms.toFixed(0)} · embed{" "}
              {result.timing.embedding_ms.toFixed(0)} · rerank{" "}
              {result.timing.rerank_ms.toFixed(0)}
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted">No run yet.</p>
        )}
        {result || offers || optimisation ? (
          <DecisionTrace
            match={result}
            offers={offers}
            optimisation={optimisation}
            hasProposal={Boolean(negotiation?.proposal)}
          />
        ) : null}
        <ol className="space-y-1">
          {(
            [
              "understand",
              "qualify",
              "match",
              "construct",
              "optimise",
              "negotiate",
              "transact",
              "learn",
            ] as const
          ).map((id) => {
            const state = processState(
              Boolean(result),
              Boolean(offers),
              Boolean(optimisation),
              Boolean(negotiation),
              Boolean(transaction),
              transaction?.state === "CONFIRMED",
              id,
            );
            return (
              <li
                key={id}
                className={`flex items-center justify-between border-l-2 px-3 py-2 text-sm ${
                  state === "complete" || state === "active"
                    ? "border-ink bg-canvas"
                    : state === "next"
                      ? "border-warning/60 bg-warning/5"
                      : "border-line"
                }`}
              >
                <span className="uppercase text-ink">{id}</span>
                <span className="text-[11px] tracking-[0.08em] text-muted">
                  {state}
                </span>
              </li>
            );
          })}
        </ol>
      </aside>

      {offers ? (
        <div className="xl:col-span-3">
          <OfferExplorer
            construction={offers}
            heroProduct={result?.semantic_matching.matches[0]?.product_name}
          />
        </div>
      ) : null}
      {optimisation ? (
        <div className="xl:col-span-3">
          <OptimisationPanel
            optimisation={optimisation}
            profile={profile}
            onProfile={(next) => void rerunOptimisation(next)}
            busy={busy}
          />
        </div>
      ) : null}
      {negotiation ? (
        <div className="xl:col-span-3">
          <NegotiationPanel
            negotiation={negotiation}
            busy={busy}
            onMessage={(message) => {
              void (async () => {
                setBusy(true);
                try {
                  const next = await postNegotiationTurn(
                    negotiation.session_id,
                    { message },
                  );
                  setNegotiation(next);
                  if (
                    next.state === "READY_FOR_CHECKOUT" &&
                    next.proposal
                  ) {
                    await executeAcceptance(next);
                  }
                } catch {
                  setError("Negotiation turn failed.");
                } finally {
                  setBusy(false);
                }
              })();
            }}
            onSimulate={(mode) => {
              void (async () => {
                setBusy(true);
                try {
                  setNegotiation(
                    await simulateNegotiationBuyer(negotiation.session_id, mode),
                  );
                } catch {
                  setError("Buyer simulation failed.");
                } finally {
                  setBusy(false);
                }
              })();
            }}
          />
        </div>
      ) : null}
      {negotiation ? (
        <div className="xl:col-span-3">
          <TransactionPanel
            negotiation={negotiation}
            transaction={transaction}
            busy={busy}
            onExecute={() => {
              void (async () => {
                setBusy(true);
                try {
                  await executeAcceptance(negotiation);
                } catch {
                  setError("Acceptance failed.");
                } finally {
                  setBusy(false);
                }
              })();
            }}
            onRecover={() => {
              void (async () => {
                setBusy(true);
                try {
                  setNegotiation(await getNegotiation(negotiation.session_id));
                  setTransaction(null);
                } catch {
                  setError("Could not reload the recovered proposal.");
                } finally {
                  setBusy(false);
                }
              })();
            }}
            onDemoInventory={(units) => {
              const sku = negotiation.proposal?.offer?.sku;
              if (!sku) return;
              void (async () => {
                setBusy(true);
                try {
                  await setDemoInventory({ sku, units_available: units });
                } catch {
                  setError("Demo inventory update failed.");
                } finally {
                  setBusy(false);
                }
              })();
            }}
            onDemoDelivery={(available) => {
              const sku = negotiation.proposal?.offer?.sku;
              if (!sku) return;
              void (async () => {
                setBusy(true);
                try {
                  await setDemoDeliveryCapacity({
                    sku,
                    delivery_code: "SAME_DAY",
                    available,
                  });
                } catch {
                  setError("Demo delivery update failed.");
                } finally {
                  setBusy(false);
                }
              })();
            }}
            onDemoMargin={(rate) => {
              void (async () => {
                setBusy(true);
                try {
                  await setDemoPolicy({ minimum_margin_rate: rate });
                  window.dispatchEvent(new Event("astraos:policy-changed"));
                } catch {
                  setError("Demo policy update failed.");
                } finally {
                  setBusy(false);
                }
              })();
            }}
          />
        </div>
      ) : null}
    </div>
  );
}

function DecisionTrace({
  match,
  offers,
  optimisation,
  hasProposal,
}: {
  match: MatchResponse | null;
  offers: GenerateOffersResponse | null;
  optimisation: OptimisationResponse | null;
  hasProposal: boolean;
}) {
  const rows = [
    match ? `${match.qualification.variants_checked} variants` : null,
    match ? `${match.qualification.eligible} eligible` : null,
    match ? `${match.semantic_matching.matches.length} semantic matches` : null,
    offers
      ? `${offers.summary.generated_candidates.toLocaleString()} offer configurations`
      : null,
    optimisation
      ? `${optimisation.summary.policy_safe.toLocaleString()} policy-safe`
      : null,
    optimisation
      ? `${optimisation.summary.pareto_efficient} Pareto efficient`
      : null,
    hasProposal ? "1 merchant proposal" : null,
  ].filter((item): item is string => item != null);
  if (!rows.length) return null;
  return (
    <div className="border border-line bg-canvas px-4 py-3 text-sm">
      <p className="eyebrow">Decision trace</p>
      <p className="mt-2 font-mono text-xs tabular-nums leading-5">{rows.join(" → ")}</p>
    </div>
  );
}

function DeepIntent({ intent }: { intent: ShoppingIntent }) {
  return (
    <div className="space-y-4 border border-line bg-canvas px-4 py-4">
      <Section title="MANDATORY">
        {intent.hard_constraints.map((item) => (
          <p key={item.id} className="text-sm">
            {fieldLabel(item.field)} {formatConstraint(item.operator, item.normalized_value ?? item.value, item.unit)}
          </p>
        ))}
      </Section>
      {intent.context_items.length ? (
        <Section title="CONTEXT">
          {intent.context_items.map((item) => (
            <p key={item.label} className="text-sm capitalize">
              {contextLabel(item.label)}
            </p>
          ))}
        </Section>
      ) : null}
      {intent.desired_outcomes.length ? (
        <Section title="DESIRED OUTCOMES">
          {intent.desired_outcomes.map((item) => (
            <p key={item.label} className="text-sm capitalize">
              {contextLabel(item.label)}
            </p>
          ))}
        </Section>
      ) : null}
      {intent.soft_preferences.length ? (
        <Section title="PREFERENCES">
          {intent.soft_preferences.map((item) => (
            <p key={item.id} className="text-sm">
              {fieldLabel(item.field)}{" "}
              <span className="text-muted">{importanceLabel(item.importance)}</span>
            </p>
          ))}
        </Section>
      ) : null}
      {intent.tradeoffs.length ? (
        <Section title="TRADE-OFF">
          {intent.tradeoffs.map((item) => (
            <p key={`${item.preferred_dimension}-${item.over_dimension}`} className="text-sm">
              {fieldLabel(item.preferred_dimension)} {">"}{" "}
              {item.over_dimension === "price"
                ? "lowest possible price"
                : fieldLabel(item.over_dimension)}
            </p>
          ))}
        </Section>
      ) : null}
      {intent.unsupported_semantic_needs.length || intent.ambiguities.length ? (
        <Section title="UNSUPPORTED / CLARIFY">
          {intent.unsupported_semantic_needs.map((item) => (
            <p key={item.label} className="text-sm text-uncertain">
              {item.source_phrase}
            </p>
          ))}
          {intent.ambiguities.map((item) => (
            <p key={item.source_phrase} className="text-sm text-uncertain">
              {item.source_phrase}
            </p>
          ))}
        </Section>
      ) : null}
    </div>
  );
}

function MatchCard({ match }: { match: RankedProductMatch }) {
  return (
    <article className="border border-line bg-canvas px-4 py-4">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-medium tracking-[0.06em] uppercase">
          #{match.rank} {match.product_name}
        </p>
        <span className="text-[11px] text-success">PASS</span>
      </div>
      <p className="font-mono text-[11px] text-muted">
        {match.sku} · {formatAudCents(match.base_price_cents)}
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-1 text-[11px]">
        <Score label="Semantic fit" value={match.overall_semantic_fit} />
        <Score label="Context fit" value={match.context_fit} />
        <Score label="Preference fit" value={match.preference_fit} />
        <Score label="Evidence" value={match.evidence_coverage} />
      </dl>
      <p className="mt-3 text-[11px] tracking-[0.12em] text-muted">WHY IT FITS</p>
      <ul className="mt-1 space-y-2">
        {match.reasons.map((reason) => (
          <li key={`${reason.kind}-${reason.need}`}>
            <p className="text-sm capitalize">{contextLabel(reason.need)}</p>
            {reason.facts.map((fact) => (
              <p key={fact.attribute} className="text-xs text-muted">
                → {fact.display}
                {fact.source_name ? ` · ${fact.source_name}` : ""}
              </p>
            ))}
          </li>
        ))}
      </ul>
      {match.unsupported_needs.length ? (
        <p className="mt-2 text-xs text-uncertain">
          Limited evidence: {match.unsupported_needs.map(contextLabel).join(", ")}
        </p>
      ) : null}
    </article>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-muted">{label}</dt>
      <dd className="tabular-nums">{pct(value)}</dd>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div>
      <p className="eyebrow">{title}</p>
      <div className="mt-2 space-y-1">{children}</div>
    </div>
  );
}

function formatConstraint(operator: string, value: unknown, unit: string | null): string {
  if (unit === "AUD_CENTS" && typeof value === "number") {
    const symbol = operator === "LT" ? "<" : operator === "LTE" ? "≤" : operator;
    return `${symbol} ${formatAudCents(value)}`;
  }
  if (unit === "DAYS" && value === 0) return "today";
  if (operator === "EQ" && value === true) return "";
  if (operator === "EQ" && value === false) return "must be false";
  return `${operator} ${String(value)}`;
}
