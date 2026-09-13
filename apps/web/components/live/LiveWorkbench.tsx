"use client";

import { useEffect, useMemo, useState } from "react";

import { BuyerContextBar } from "@/components/live/BuyerContextBar";
import { DecisionWorkflow } from "@/components/live/DecisionWorkflow";
import { NegotiationPanel } from "@/components/live/NegotiationPanel";
import { LIVE_STAGES, type LiveStage } from "@/components/live/ProcessRail";
import {
  StageFooter,
  StageHeader,
  StageLayout,
} from "@/components/live/StageShell";
import { ConstructStage } from "@/components/live/stages/ConstructStage";
import { LearnStage } from "@/components/live/stages/LearnStage";
import { MatchStage } from "@/components/live/stages/MatchStage";
import { OptimiseStage } from "@/components/live/stages/OptimiseStage";
import { QualifyStage } from "@/components/live/stages/QualifyStage";
import { UnderstandStage } from "@/components/live/stages/UnderstandStage";
import { TransactionPanel } from "@/components/live/TransactionPanel";
import { STAGE_META, stageReachable } from "@/lib/liveStages";
import { AstraLoadingState } from "@/components/astra";
import { LiveEntry } from "@/components/live/LiveEntry";
import { Drawer } from "@/components/shared/Drawer";
import { EmptyState, ErrorState } from "@/components/shared/EmptyState";
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
import { PIPELINE_LOADING } from "@/lib/decisionNarrative";
import { HERO_INTENT } from "@/lib/intent";
import type {
  BuyerProfile,
  GenerateOffersResponse,
  MatchResponse,
  AcceptProposalResponse,
  NegotiationResponse,
  OptimisationResponse,
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
    optimisation?.recommended_offer ??
    null;
  const topMatch = result?.semantic_matching.matches[0] ?? null;

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

  function editRequest() {
    setResult(null);
    setOffers(null);
    setOptimisation(null);
    setNegotiation(null);
    setTransaction(null);
    setSelectedOfferId(null);
    setError(null);
    setStage("understand");
  }

  const nextStage = LIVE_STAGES[LIVE_STAGES.indexOf(stage) + 1];
  const onContinue =
    nextStage &&
    STAGE_META[stage].continueLabel &&
    stageReachable(nextStage, flags, stage)
      ? () => setStage(nextStage)
      : undefined;

  const stageMain = (() => {
    if (stage === "understand" && result) {
      return (
        <UnderstandStage
          intent={result.intent}
          rawText={text}
          onInspect={() => setInspect(true)}
          onContinue={onContinue}
        />
      );
    }
    if (stage === "qualify" && result) {
      return (
        <QualifyStage
          qualification={result.qualification}
          intentText={text}
          parserMode={parserMode}
          onContinue={onContinue}
        />
      );
    }
    if (stage === "match" && result) {
      return (
        <MatchStage
          matches={result.semantic_matching.matches}
          onContinue={onContinue}
        />
      );
    }
    if (stage === "construct" && offers) {
      return (
        <ConstructStage
          construction={offers}
          optimisation={optimisation}
          heroProduct={topMatch?.product_name}
          onContinue={onContinue}
        />
      );
    }
    if (stage === "optimise" && optimisation) {
      return (
        <OptimiseStage
          optimisation={optimisation}
          offer={proposalOffer}
          topMatch={topMatch}
          construction={offers}
          profile={profile}
          busy={busy}
          selectedOfferId={selectedOfferId}
          onProfile={(next) => void rerunOptimisation(next)}
          onSelectOffer={setSelectedOfferId}
          onContinue={onContinue}
        />
      );
    }
    if (stage === "negotiate" && negotiation) {
      return (
        <NegotiationPanel
          negotiation={negotiation}
          busy={busy}
          onMessage={(message) => {
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
      );
    }
    if (stage === "transact" && negotiation) {
      return (
        <TransactionPanel
          negotiation={negotiation}
          transaction={transaction}
          busy={busy}
          onExecute={() => {
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
      );
    }
    if (stage === "learn") {
      return (
        <LearnStage negotiation={negotiation} transaction={transaction} />
      );
    }
    return (
      <EmptyState
        title="Stage unavailable"
        body="This stage is not available for the current run."
      />
    );
  })();

  return (
    <div>
      <DecisionWorkflow
        active={stage}
        flags={flags}
        onSelect={setStage}
      />
      <div className="space-y-5 pt-5">
        {error ? <ErrorState message={error} /> : null}
        {result ? (
          <BuyerContextBar
            intent={result.intent}
            rawText={text}
            onEdit={editRequest}
            onRerun={() => void run()}
            busy={busy}
          />
        ) : null}
        <StageHeader stage={stage} />
        <StageLayout wide={stage === "construct"}>{stageMain}</StageLayout>
        <StageFooter stage={stage} flags={flags} onSelect={setStage} />
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
