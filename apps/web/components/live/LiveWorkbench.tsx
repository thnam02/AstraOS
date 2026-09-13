"use client";

import { useEffect, useMemo, useState } from "react";

import { ApiStatus } from "@/components/live/ApiStatus";
import { DecisionBridge } from "@/components/live/DecisionBridge";
import { IntentPanel } from "@/components/live/IntentPanel";
import { MatchList } from "@/components/live/MatchList";
import { NegotiationPanel } from "@/components/live/NegotiationPanel";
import { OfferExplorer } from "@/components/live/OfferExplorer";
import { OptimisationPanel } from "@/components/live/OptimisationPanel";
import { ProcessRail, type LiveStage } from "@/components/live/ProcessRail";
import { QualificationInspect } from "@/components/live/QualificationInspect";
import { RecommendedOffer } from "@/components/live/RecommendedOffer";
import { TransactionPanel } from "@/components/live/TransactionPanel";
import { AstraLoadingState } from "@/components/astra";
import { LiveEntry } from "@/components/live/LiveEntry";
import { Drawer } from "@/components/shared/Drawer";
import { EmptyState, ErrorState } from "@/components/shared/EmptyState";
import { StatStrip } from "@/components/shared/StatStrip";
import {
  acceptProposal,
  createNegotiation,
  getNegotiation,
  postNegotiationTurn,
  reselectOptimisation,
  runOptimisation,
  setDemoDeliveryCapacity,
  setDemoInventory,
  setDemoPolicy,
  simulateNegotiationBuyer,
} from "@/lib/api";
import { PIPELINE_LOADING, productsDiffer } from "@/lib/decisionNarrative";
import { HERO_INTENT } from "@/lib/intent";
import type {
  BuyerProfile,
  GenerateOffersResponse,
  MatchResponse,
  AcceptProposalResponse,
  NegotiationResponse,
  OptimisationResponse,
  PublicScoredOffer,
} from "@/types";

export function LiveWorkbench() {
  const [text, setText] = useState(HERO_INTENT);
  const [parserMode, setParserMode] = useState<"rule_based" | "llm">("llm");
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
  const [stage, setStage] = useState<LiveStage>("understand");
  const [inspect, setInspect] = useState(false);
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);

  const selectedFromChart = useMemo(() => {
    if (!selectedOfferId || !optimisation) return null;
    return (
      optimisation.pareto_offers.find((item) => item.offer_id === selectedOfferId) ??
      (optimisation.recommended_offer?.offer_id === selectedOfferId
        ? optimisation.recommended_offer
        : null)
    );
  }, [optimisation, selectedOfferId]);
  const proposalOffer =
    selectedFromChart ??
    negotiation?.proposal?.offer ??
    optimisation?.recommended_offer ??
    null;
  const proposalWhy =
    negotiation?.proposal?.explanation ?? optimisation?.explanation ?? [];
  const topMatch = result?.semantic_matching.matches[0] ?? null;
  const differ = productsDiffer(topMatch, proposalOffer);

  const flags = {
    hasMatch: Boolean(result),
    hasOffers: Boolean(offers),
    hasOpt: Boolean(optimisation),
    hasNego: Boolean(negotiation),
    hasTxn: Boolean(transaction),
    txnFailed: Boolean(
      transaction &&
        transaction.state !== "CONFIRMED" &&
        transaction.failure_codes.length > 0,
    ),
    txnComplete: transaction?.state === "CONFIRMED",
  };

  async function executeAcceptance(session: NegotiationResponse) {
    if (!session.proposal) return;
    const accepted = await acceptProposal(session.session_id, {
      proposal_id: session.proposal.proposal_id,
      idempotency_key:
        globalThis.crypto?.randomUUID?.() ?? `web-${Date.now()}`,
    });
    setTransaction(accepted);
    setNegotiation(await getNegotiation(session.session_id));
  }

  async function run(nextText = text, nextProfile = profile) {
    setBusy(true);
    setError(null);
    try {
      const decided = await createNegotiation({
        intent: nextText,
        parser_mode: parserMode,
        buyer_profile: nextProfile,
        max_products: 8,
      });
      if (decided.match) setResult(decided.match);
      if (decided.construction) setOffers(decided.construction);
      if (decided.optimisation) setOptimisation(decided.optimisation);
      setNegotiation(decided);
      setTransaction(null);
      setSelectedOfferId(null);
      setStage("match");
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

  async function reselectForObjective() {
    if (!optimisation) return;
    setBusy(true);
    setError(null);
    try {
      const next = await reselectOptimisation(optimisation.optimisation_run_id);
      setOptimisation(next);
      if (next.recommended_offer) {
        setSelectedOfferId(next.recommended_offer.offer_id);
      }
    } catch {
      setError("Objective reselection failed.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    function onPolicy() {
      if (!offers) return;
      void rerunOptimisation(profile);
    }
    function onObjective() {
      if (!optimisation) return;
      void reselectForObjective();
    }
    window.addEventListener("astraos:policy-changed", onPolicy);
    window.addEventListener("astraos:objective-changed", onObjective);
    return () => {
      window.removeEventListener("astraos:policy-changed", onPolicy);
      window.removeEventListener("astraos:objective-changed", onObjective);
    };
  }, [offers, profile, optimisation]);

  if (!result && busy) {
    return (
      <AstraLoadingState
        title="Creating a merchant response"
        steps={PIPELINE_LOADING}
      />
    );
  }

  if (!result && !busy) {
    return (
      <LiveEntry
        text={text}
        parserMode={parserMode}
        error={error}
        onText={setText}
        onParser={setParserMode}
        onRun={() => void run()}
        onScenario={(intent, nextProfile) => {
          setText(intent);
          setProfile(nextProfile);
          void run(intent, nextProfile);
        }}
        onCustom={() => setText(HERO_INTENT)}
      />
    );
  }

  const centerWide = stage === "optimise" || stage === "negotiate" || stage === "transact";

  return (
    <div className="space-y-4">
      <section className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="eyebrow">Buyer agent request</p>
            <p className="mt-1 max-w-3xl text-sm leading-6">“{text}”</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <select
                value={parserMode}
                onChange={(event) =>
                  setParserMode(event.target.value as "rule_based" | "llm")
                }
                className="control px-2 py-1 text-xs"
              >
                <option value="rule_based">Rule-based parser</option>
                <option value="llm">LLM parser</option>
              </select>
              <button
                type="button"
                onClick={() => void run()}
                disabled={busy || !text.trim()}
                className="btn-primary"
              >
                {busy ? "Running…" : "Run AstraOS"}
              </button>
            </div>
          </div>
          <ApiStatus />
        </div>
        {error ? <ErrorState message={error} /> : null}
        <ProcessRail active={stage} flags={flags} onSelect={setStage} />
      </section>

      <div
        className={`grid gap-6 ${
          centerWide
            ? "xl:grid-cols-[minmax(180px,0.18fr)_minmax(0,0.57fr)_minmax(260px,0.25fr)]"
            : "xl:grid-cols-[minmax(200px,0.2fr)_minmax(0,0.55fr)_minmax(280px,0.25fr)]"
        }`}
      >
        <aside>
          <p className="eyebrow">What the buyer asked</p>
          {result && stage !== "understand" ? (
            <div className="mt-3">
              <IntentPanel intent={result.intent} compact />
            </div>
          ) : result ? (
            <p className="mt-3 text-sm leading-6 text-muted">
              Structured constraints, context, and priorities are shown in the
              current stage.
            </p>
          ) : (
            <p className="mt-3 text-sm text-muted">Extracting structured intent…</p>
          )}
        </aside>

        <section className="min-w-0 space-y-4">
          <StageView
            stage={stage}
            result={result}
            offers={offers}
            optimisation={optimisation}
            negotiation={negotiation}
            transaction={transaction}
            profile={profile}
            busy={busy}
            parserMode={parserMode}
            intentText={text}
            onProfile={(next) => void rerunOptimisation(next)}
            onMessage={(message) => {
              if (!negotiation) return;
              void (async () => {
                setBusy(true);
                try {
                  const next = await postNegotiationTurn(negotiation.session_id, {
                    message,
                  });
                  setNegotiation(next);
                  if (next.state === "READY_FOR_CHECKOUT" && next.proposal) {
                    await executeAcceptance(next);
                    setStage("transact");
                  }
                } catch {
                  setError("Negotiation turn failed.");
                } finally {
                  setBusy(false);
                }
              })();
            }}
            onSimulate={(mode) => {
              if (!negotiation) return;
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
            onExecute={() => {
              if (!negotiation) return;
              void (async () => {
                setBusy(true);
                try {
                  await executeAcceptance(negotiation);
                  setStage("transact");
                } catch {
                  setError("Acceptance failed.");
                } finally {
                  setBusy(false);
                }
              })();
            }}
            onRecover={() => {
              if (!negotiation) return;
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
              const sku = negotiation?.proposal?.offer?.sku;
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
              const sku = negotiation?.proposal?.offer?.sku;
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
            selectedOfferId={selectedOfferId}
            onSelectOffer={setSelectedOfferId}
            topMatchName={topMatch?.product_name}
            matchCount={result?.semantic_matching.matches.length}
            proposal={proposalOffer}
            optimisationSummary={optimisation?.summary}
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
        </section>

        <aside className="panel-decision h-fit xl:sticky xl:top-20">
          {proposalOffer ? (
            <RecommendedOffer
              offer={proposalOffer}
              explanation={proposalWhy}
              onWhyDifferent={
                differ ? () => setStage("match") : undefined
              }
              objective={optimisation?.merchant_objective}
              selection={optimisation?.selection}
              topMatch={topMatch}
            />
          ) : (
            <EmptyState
              title="Selected commercial offer"
              body="The merchant response appears here after optimisation."
            />
          )}
          <button
            type="button"
            className="btn-quiet mt-4"
            onClick={() => setInspect(true)}
          >
            Inspect decision
          </button>
        </aside>
      </div>
      <Drawer open={inspect} title="Inspect decision" onClose={() => setInspect(false)}>
        <div className="space-y-4 text-sm">
          <section>
            <p className="eyebrow">Parser</p>
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              {Object.entries({
                parser_requested: result?.intent.parser_metadata?.parser_requested,
                parser_used: result?.intent.parser_metadata?.parser_used ?? result?.intent.parser_type,
                provider: result?.intent.parser_metadata?.provider,
                model: result?.intent.parser_metadata?.model,
                prompt_version: result?.intent.parser_metadata?.prompt_version,
                schema_version: result?.intent.parser_metadata?.schema_version,
                fallback_used: result?.intent.parser_metadata?.fallback_used ?? false,
                fallback_reason: result?.intent.parser_metadata?.fallback_reason,
                repair_count: result?.intent.parser_metadata?.repair_count ?? 0,
                latency_ms: result?.intent.parser_metadata?.latency_ms,
                input_tokens: result?.intent.parser_metadata?.input_tokens,
                output_tokens: result?.intent.parser_metadata?.output_tokens,
                total_tokens: result?.intent.parser_metadata?.total_tokens,
              }).map(([key, value]) => (
                <div key={key} className="contents">
                  <dt className="text-muted">{key}</dt>
                  <dd>{value === null || value === undefined || value === "" ? "—" : String(value)}</dd>
                </div>
              ))}
            </dl>
          </section>
          <section>
            <p className="eyebrow">Embeddings</p>
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              {Object.entries({
                provider_requested: result?.semantic_matching.provider_requested,
                provider_used: result?.semantic_matching.provider_used,
                model: result?.semantic_matching.model,
                dimension: result?.semantic_matching.dimension,
                document_version: result?.semantic_matching.document_version,
                retrieval_version: result?.semantic_matching.retrieval_version,
                rerank_version: result?.semantic_matching.rerank_version,
                fallback_used: result?.semantic_matching.fallback_used ?? false,
                fallback_reason: result?.semantic_matching.fallback_reason,
              }).map(([key, value]) => (
                <div key={key} className="contents">
                  <dt className="text-muted">{key}</dt>
                  <dd>{value === null || value === undefined || value === "" ? "—" : String(value)}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-2 text-xs text-muted">
              Product / context / preference scores are grounded rerank points
              out of 100, not purchase probability or raw cosine similarity.
            </p>
          </section>
          <pre className="overflow-x-auto text-[11px] text-muted">
            {JSON.stringify(
              {
                qualification: result?.qualification,
                top_match: topMatch,
                construction: offers?.summary,
                optimisation: optimisation?.summary,
                merchant_objective: optimisation?.merchant_objective,
                selection: optimisation?.selection,
                selected_offer: proposalOffer,
                run_ids: {
                  match: result?.run_id,
                  offer: offers?.offer_run_id,
                  optimisation: optimisation?.optimisation_run_id,
                  negotiation: negotiation?.session_id,
                },
              },
              null,
              2,
            )}
          </pre>
        </div>
      </Drawer>
    </div>
  );
}

function StageView({
  stage,
  result,
  offers,
  optimisation,
  negotiation,
  transaction,
  profile,
  busy,
  parserMode,
  intentText,
  onProfile,
  onMessage,
  onSimulate,
  onExecute,
  onRecover,
  onDemoInventory,
  onDemoDelivery,
  onDemoMargin,
  selectedOfferId,
  onSelectOffer,
  optimisationSummary,
  topMatchName,
  matchCount,
  proposal,
}: {
  stage: LiveStage;
  result: MatchResponse | null;
  offers: GenerateOffersResponse | null;
  optimisation: OptimisationResponse | null;
  negotiation: NegotiationResponse | null;
  transaction: AcceptProposalResponse | null;
  profile: BuyerProfile;
  busy: boolean;
  parserMode: "rule_based" | "llm";
  intentText: string;
  selectedOfferId: string | null;
  onSelectOffer: (offerId: string) => void;
  optimisationSummary?: OptimisationResponse["summary"];
  topMatchName?: string;
  matchCount?: number;
  proposal: PublicScoredOffer | null;
  onProfile: (profile: BuyerProfile) => void;
  onMessage: (message: string) => void;
  onSimulate: (mode: "TRAVEL" | "BUDGET") => void;
  onExecute: () => void;
  onRecover: () => void;
  onDemoInventory: (units: number) => void;
  onDemoDelivery: (available: boolean) => void;
  onDemoMargin: (rate: number) => void;
}) {
  if (stage === "understand") {
    if (!result) {
      return (
        <EmptyState
          title="Understand"
          body="Run AstraOS to extract constraints, context, and trade-offs."
        />
      );
    }
    return (
      <div className="space-y-3">
        <p className="eyebrow">Understand</p>
        <h2 className="text-xl font-semibold tracking-tight">
          Structured intent
        </h2>
        <p className="text-sm text-muted">
          Language is interpreted. No commercial terms are decided here.
        </p>
        <IntentPanel intent={result.intent} />
      </div>
    );
  }

  if (stage === "qualify") {
    if (!result) {
      return (
        <EmptyState
          title="Qualification"
          body="Run AstraOS to check mandatory eligibility."
        />
      );
    }
    return (
      <div className="space-y-3">
        <p className="eyebrow">Qualify</p>
        <h2 className="text-xl font-semibold tracking-tight">Eligibility</h2>
        <StatStrip
          items={[
            { label: "Variants", value: result.qualification.variants_checked },
            { label: "Eligible", value: result.qualification.eligible },
            { label: "Violated", value: result.qualification.violated },
            { label: "Unknown", value: result.qualification.uncertain },
          ]}
        />
        <QualificationInspect intentText={intentText} parserMode={parserMode} />
        <p className="text-xs text-muted">
          Semantic ranking runs only on eligible SKUs.
        </p>
      </div>
    );
  }

  if (stage === "match") {
    if (!result) {
      return (
        <EmptyState
          title="Match"
          body="Run AstraOS to rank eligible products by overall match."
        />
      );
    }
    return (
      <div className="space-y-4">
        <div>
          <p className="eyebrow">Product decision</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">
            Standalone product ranking
          </h2>
          <p className="mt-1 text-xs text-muted">
            What product best fits the buyer’s needs — not yet a commercial offer.
          </p>
        </div>
        <MatchList matches={result.semantic_matching.matches} />
        {proposal && offers ? (
          <DecisionBridge
            topMatch={result.semantic_matching.matches[0] ?? null}
            construction={offers}
            optimisation={optimisation}
            offer={proposal}
          />
        ) : null}
        <p className="text-xs text-muted">
          {result.timing.total_ms.toFixed(0)} ms · parse{" "}
          {result.timing.intent_parse_ms.toFixed(0)} · qualify{" "}
          {result.timing.qualification_ms.toFixed(0)}
        </p>
      </div>
    );
  }

  if (stage === "construct") {
    if (!offers) {
      return (
        <EmptyState
          title="Construct"
          body="Offer space is built after matching."
        />
      );
    }
    return (
      <OfferExplorer
        construction={offers}
        heroProduct={result?.semantic_matching.matches[0]?.product_name}
        policySafe={optimisationSummary?.policy_safe}
        pareto={optimisationSummary?.pareto_efficient}
      />
    );
  }

  if (stage === "optimise") {
    if (!optimisation) {
      return (
        <EmptyState
          title="Optimise"
          body="The Pareto frontier appears after construction."
        />
      );
    }
    return (
      <OptimisationPanel
        optimisation={optimisation}
        profile={profile}
        onProfile={onProfile}
        busy={busy}
        showRecommendation={false}
        selectedOfferId={selectedOfferId}
        onSelectOffer={onSelectOffer}
        productSummary={
          topMatchName
            ? `${matchCount ?? 0} products ranked · top ${topMatchName}`
            : undefined
        }
      />
    );
  }

  if (stage === "negotiate") {
    if (!negotiation) {
      return (
        <EmptyState
          title="Negotiate"
          body="A merchant proposal is required before counters."
        />
      );
    }
    return (
      <NegotiationPanel
        negotiation={negotiation}
        busy={busy}
        onMessage={onMessage}
        onSimulate={onSimulate}
      />
    );
  }

  if (stage === "transact") {
    if (!negotiation) {
      return (
        <EmptyState
          title="Transact"
          body="Accept a proposal to reserve inventory and write the order."
        />
      );
    }
    return (
      <TransactionPanel
        negotiation={negotiation}
        transaction={transaction}
        busy={busy}
        onExecute={onExecute}
        onRecover={onRecover}
        onDemoInventory={onDemoInventory}
        onDemoDelivery={onDemoDelivery}
        onDemoMargin={onDemoMargin}
      />
    );
  }

  return (
    <EmptyState
      title="Learn"
      body="Transaction outcomes feed LEARN. Open the LEARN destination for calibration and model status."
    />
  );
}
