"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { BenchmarkView } from "@/components/arena/BenchmarkView";
import { BuyerDecision } from "@/components/arena/BuyerDecision";
import { ExperimentInspector } from "@/components/arena/ExperimentInspector";
import { StrategyCard } from "@/components/arena/StrategyCard";
import { StrategyComparison } from "@/components/arena/StrategyComparison";
import {
  AstraErrorState,
  AstraLoadingState,
  AstraPanel,
  AstraSectionHeader,
} from "@/components/astra";
import { Drawer } from "@/components/shared/Drawer";
import {
  arenaBenchmarkExportUrl,
  createArenaBenchmark,
  getArenaBenchmark,
  getLatestArenaBenchmark,
  runArenaDuel,
} from "@/lib/api";
import {
  bundleLabel,
  commercialDifference,
  deliveryLabel,
  findStrategy,
  headline,
  isSelectable,
  moneyDelta,
  qualitativePriorities,
  returnsLabel,
  selectedStrategy,
  signedDelta,
  strategyTitle,
  strongestBaseline,
  validResponses,
  warrantyLabel,
} from "@/lib/arenaDisplay";
import { formatUtilityShort } from "@/lib/format";
import { formatAudCents } from "@/lib/money";
import { cn } from "@/lib/utils";
import type {
  ArenaBenchmarkResponse,
  ArenaRunResponse,
  BuyerProfile,
} from "@/types";

const CORE_STRATEGIES = [
  "DEFAULT",
  "ALWAYS_DISCOUNT",
  "SEMANTIC_ONLY",
  "ASTRAOS",
] as const;

const EXTENDED_STRATEGIES = [
  "DEFAULT",
  "ALWAYS_DISCOUNT",
  "CHEAPEST_ELIGIBLE",
  "SEMANTIC_ONLY",
  "ASTRAOS",
] as const;

const ARENA_HERO =
  "I need ANC headphones under A$350 for a long-haul flight. Delivered today. Comfort and reliability matter more than getting the cheapest option.";

const PRESETS = [
  {
    id: "urgent",
    label: "Urgent traveller",
    title: "Urgent traveller",
    profile: "URGENT_TRAVELLER" as BuyerProfile,
    intent: ARENA_HERO,
  },
  {
    id: "budget",
    label: "Budget buyer",
    title: "Budget buyer",
    profile: "BUDGET_SHOPPER" as BuyerProfile,
    intent:
      "I need wireless ANC headphones under A$260. Cheapest option that still works is fine. Two-day delivery is ok.",
  },
  {
    id: "assurance",
    label: "Assurance buyer",
    title: "Assurance buyer",
    profile: "ASSURANCE_BUYER" as BuyerProfile,
    intent:
      "I want reliable ANC headphones under A$350. A long warranty matters more than getting the cheapest pair.",
  },
] as const;

const STRATEGY_OPTIONS = [
  { id: "DEFAULT", label: "Default" },
  { id: "ALWAYS_DISCOUNT", label: "Always Discount" },
  { id: "SEMANTIC_ONLY", label: "Semantic Only" },
  { id: "ASTRAOS", label: "AstraOS" },
  { id: "CHEAPEST_ELIGIBLE", label: "Cheapest Eligible", extra: true },
] as const;

export function ArenaWorkbench() {
  const [view, setView] = useState<"setup" | "results">("setup");
  const [detail, setDetail] = useState<
    "buyer" | "comparison" | "semantic" | "methodology" | null
  >(null);
  const [strategyInspect, setStrategyInspect] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<"duel" | "benchmark">("duel");
  const [scenario, setScenario] = useState<string>("urgent");
  const [intent, setIntent] = useState(ARENA_HERO);
  const [profile, setProfile] = useState<BuyerProfile>("URGENT_TRAVELLER");
  const [editing, setEditing] = useState(false);
  const [duel, setDuel] = useState<ArenaRunResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [missionCount, setMissionCount] = useState(100);
  const [seed, setSeed] = useState(2026);
  const [benchmark, setBenchmark] = useState<ArenaBenchmarkResponse | null>(
    null,
  );
  const [inspect, setInspect] = useState(false);
  const [moreStrategies, setMoreStrategies] = useState(false);

  const preset = PRESETS.find((item) => item.id === scenario);
  const custom = scenario === "custom";

  useEffect(() => {
    void getLatestArenaBenchmark()
      .then((row) => {
        if (row) setBenchmark(row);
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Unable to load benchmark",
        );
      });
  }, []);

  useEffect(() => {
    if (view === "results" && !busy)
      resultsRef.current?.focus({ preventScroll: true });
  }, [view, busy]);

  async function onDuel() {
    setBusy(true);
    setError(null);
    try {
      setDuel(
        await runArenaDuel({
          intent,
          buyer_profile: profile,
          strategies: moreStrategies
            ? [...EXTENDED_STRATEGIES]
            : [...CORE_STRATEGIES],
        }),
      );
      setView("results");
    } catch (err) {
      setView("setup");
      setError(err instanceof Error ? err.message : "Arena run failed");
    } finally {
      setBusy(false);
    }
  }

  async function onBenchmark() {
    setBusy(true);
    setError(null);
    try {
      const created = await createArenaBenchmark({
        mission_count: missionCount,
        seed,
      });
      setBenchmark(await getArenaBenchmark(created.benchmark_id));
      setView("results");
    } catch (err) {
      setView("setup");
      setError(err instanceof Error ? err.message : "Benchmark failed");
    } finally {
      setBusy(false);
    }
  }

  function applyPreset(id: string) {
    const next = PRESETS.find((item) => item.id === id);
    if (!next) {
      setScenario("custom");
      setEditing(true);
      return;
    }
    setScenario(next.id);
    setIntent(next.intent);
    setProfile(next.profile);
    setEditing(false);
  }

  const winner = duel ? selectedStrategy(duel) : null;
  const baseline = duel ? strongestBaseline(duel) : null;
  const cheapest = duel
    ? [...validResponses(duel)].sort(
        (a, b) =>
          (a.total_customer_price_cents ?? 0) -
          (b.total_customer_price_cents ?? 0),
      )[0]
    : null;
  const summary = duel ? headline(duel) : null;
  const defaultOffer = duel?.strategies.find(
    (item) => item.response.strategy_name === "DEFAULT",
  )?.response;
  const highlights = useMemo(
    () => (duel ? evaluationHighlights(duel) : null),
    [duel],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1 border-y border-line py-2 text-xs text-muted">
        <p>
          Same buyer, catalogue, inventory, policy and buyer model.{" "}
          <span className="font-medium text-ink">Only strategy changes.</span>
        </p>
        <p>Synthetic evaluation · not observed sales uplift</p>
      </div>

      {!busy && view === "setup" ? (
        <AstraPanel>
          <AstraSectionHeader
            eyebrow="Experiment setup"
            action={
              (mode === "duel" ? duel : benchmark) ? (
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => setView("results")}
                >
                  View last results
                </button>
              ) : undefined
            }
            title={
              mode === "duel"
                ? "Configure one buyer mission"
                : "Configure benchmark run"
            }
            description={
              mode === "duel"
                ? "Choose a scenario, confirm strategies, then run evaluation."
                : "Set mission count and seed for a reproducible controlled benchmark."
            }
          />

          <div className="mt-4 flex gap-1 border-b border-line pb-3">
            <ModeTab
              active={mode === "duel"}
              label="Live duel"
              hint="One buyer mission"
              onClick={() => setMode("duel")}
            />
            <ModeTab
              active={mode === "benchmark"}
              label="Benchmark"
              hint="Mission set"
              onClick={() => setMode("benchmark")}
            />
          </div>
          <p className="mt-2 type-small text-muted">
            {mode === "duel"
              ? "Compare strategies on one selected buyer mission."
              : "Compare strategies across the controlled mission set."}
          </p>

          {mode === "duel" ? (
            <div className="mt-4 grid gap-5 lg:grid-cols-2">
              <div className="space-y-3">
                <div>
                  <p className="text-xs tracking-[0.08em] text-muted">
                    SCENARIO PRESETS
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {PRESETS.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        aria-pressed={scenario === item.id}
                        className={cn(
                          "border px-3 py-1.5 text-sm",
                          "rounded-[var(--radius-control)]",
                          scenario === item.id
                            ? "border-ink bg-ink text-surface"
                            : "border-line bg-surface text-ink hover:border-ink",
                        )}
                        onClick={() => applyPreset(item.id)}
                      >
                        {item.label}
                      </button>
                    ))}
                    <button
                      type="button"
                      aria-pressed={custom}
                      className={cn(
                        "border px-3 py-1.5 text-sm",
                        "rounded-[var(--radius-control)]",
                        custom
                          ? "border-ink bg-ink text-surface"
                          : "border-line bg-surface text-ink hover:border-ink",
                      )}
                      onClick={() => applyPreset("custom")}
                    >
                      Custom
                    </button>
                  </div>
                </div>

                <div className="border-t border-line pt-4">
                  <p className="text-xs tracking-[0.08em] text-muted">
                    BUYER MISSION
                  </p>
                  {custom || editing ? (
                    <textarea
                      aria-label="Buyer mission"
                      className="control mt-2 h-24 w-full p-3 text-sm"
                      value={intent}
                      onChange={(event) => {
                        setIntent(event.target.value);
                        setScenario("custom");
                      }}
                    />
                  ) : (
                    <div className="mt-2 space-y-2">
                      <p className="font-medium">
                        {preset?.title ?? "Mission"}
                      </p>
                      <p className="text-sm leading-6 text-ink">“{intent}”</p>
                      <button
                        type="button"
                        className="btn-quiet"
                        onClick={() => setEditing(true)}
                      >
                        Edit mission
                      </button>
                    </div>
                  )}
                </div>

                <div>
                  <p className="text-xs tracking-[0.08em] text-muted">
                    PRIORITIES
                  </p>
                  <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                    {qualitativePriorities(profile).map((item) => (
                      <div
                        key={item.label}
                        className="flex justify-between gap-3 border-b border-line py-1.5 last:border-0"
                      >
                        <dt>{item.label}</dt>
                        <dd className="text-muted">{item.level}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="text-xs tracking-[0.08em] text-muted">
                    STRATEGIES
                  </p>
                  <ul className="mt-2 space-y-2 text-sm">
                    {STRATEGY_OPTIONS.filter(
                      (item) =>
                        moreStrategies || !("extra" in item && item.extra),
                    ).map((item) => (
                      <li
                        key={item.id}
                        className="flex items-center gap-2 border-b border-line py-1.5 last:border-0"
                      >
                        <span
                          aria-hidden
                          className="inline-flex h-4 w-4 items-center justify-center border border-ink bg-ink text-[10px] text-surface"
                        >
                          ✓
                        </span>
                        <span>{item.label}</span>
                      </li>
                    ))}
                  </ul>
                  <button
                    type="button"
                    className="btn-quiet mt-2"
                    onClick={() => setMoreStrategies((current) => !current)}
                  >
                    {moreStrategies
                      ? "Hide optional strategies"
                      : "+ More strategies"}
                  </button>
                  <p className="mt-2 type-small text-muted">
                    Same merchant state for every strategy. Methodology details
                    are in evaluation notes after the run.
                  </p>
                </div>

                <div className="flex justify-end border-t border-line pt-4">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => void onDuel()}
                    disabled={busy || !intent.trim()}
                  >
                    {busy ? "Running…" : "Run evaluation"}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
              <div className="flex flex-wrap gap-3">
                <label className="text-xs text-muted">
                  Missions
                  <input
                    className="control mt-1 block w-28 px-2 py-1.5"
                    type="number"
                    min={8}
                    max={2000}
                    value={missionCount}
                    onChange={(event) =>
                      setMissionCount(Number(event.target.value))
                    }
                  />
                </label>
                <label className="text-xs text-muted">
                  Seed
                  <input
                    className="control mt-1 block w-28 px-2 py-1.5"
                    type="number"
                    value={seed}
                    onChange={(event) => setSeed(Number(event.target.value))}
                  />
                </label>
              </div>
              <button
                type="button"
                className="btn-primary"
                onClick={() => void onBenchmark()}
                disabled={busy}
              >
                {busy ? "Running…" : "Run benchmark"}
              </button>
            </div>
          )}
        </AstraPanel>
      ) : null}

      {error ? (
        <AstraErrorState
          title="Evaluation failed"
          message={error}
          next="Adjust the setup and run again."
        />
      ) : null}

      {busy ? (
        <AstraPanel>
          <AstraLoadingState
            title={
              mode === "duel"
                ? "Running strategy comparison"
                : "Running benchmark"
            }
            steps={
              mode === "duel"
                ? [
                    "Applying shared merchant state",
                    "Evaluating each strategy",
                    "Scoring simulated buyer selection",
                  ]
                : [
                    "Sampling controlled missions",
                    "Evaluating strategies",
                    "Aggregating metrics",
                  ]
            }
          />
        </AstraPanel>
      ) : view === "results" ? (
        <div
          ref={resultsRef}
          tabIndex={-1}
          aria-label="Evaluation results"
          className="focus:outline-none"
        >
          <AstraPanel tone="primary">
            <AstraSectionHeader
              eyebrow="Results"
              title={
                mode === "duel" ? "Strategy comparison" : "Benchmark results"
              }
              action={
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => setView("setup")}
                  >
                    Edit experiment
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() =>
                      void (mode === "duel" ? onDuel() : onBenchmark())
                    }
                  >
                    Run again
                  </button>
                </div>
              }
            />
            {mode === "duel" && duel ? (
              <div className="mt-4 space-y-4">
                {summary ? (
                  <div className="grid items-center gap-4 border-y border-line py-3 lg:grid-cols-[minmax(0,1fr)_auto]">
                    <div>
                      <h2 className="text-xl font-semibold tracking-tight">
                        {summary.title}
                      </h2>
                      <p className="mt-1 max-w-3xl text-sm text-muted">
                        {summary.body}
                      </p>
                    </div>
                    {winner ? (
                      <dl className="flex gap-6 text-sm">
                        <div>
                          <dt className="text-muted">Buyer utility</dt>
                          <dd className="font-mono text-xl font-semibold tabular-nums">
                            {winner.buyer_utility != null
                              ? formatUtilityShort(winner.buyer_utility)
                              : "—"}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted">Contribution</dt>
                          <dd className="font-mono text-xl font-semibold tabular-nums">
                            {winner.merchant_contribution_cents != null
                              ? formatAudCents(
                                  winner.merchant_contribution_cents,
                                )
                              : "—"}
                          </dd>
                        </div>
                      </dl>
                    ) : null}
                  </div>
                ) : null}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <caption className="sr-only">
                      Strategy results under identical commercial conditions
                    </caption>
                    <thead className="border-b border-line text-xs text-muted">
                      <tr>
                        <th className="py-2 pr-4">Strategy / product</th>
                        <th className="px-3 py-2 text-right">Price</th>
                        <th className="px-3 py-2 text-right">Buyer utility</th>
                        <th className="px-3 py-2 text-right">Contribution</th>
                        <th className="px-3 py-2">Outcome</th>
                        <th className="py-2">
                          <span className="sr-only">Details</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {duel.strategies.map(({ response }) => {
                        const selected =
                          !duel.buyer_selection.no_purchase &&
                          duel.buyer_selection.selected_strategy ===
                            response.strategy_name;
                        const valid = isSelectable(response);
                        return (
                          <tr
                            key={response.strategy_name}
                            className={cn(
                              "border-b border-line-muted",
                              selected && "bg-canvas",
                            )}
                          >
                            <th scope="row" className="py-3 pr-4 font-normal">
                              <p className="font-semibold">
                                {strategyTitle(response.strategy_name)}
                              </p>
                              <p className="mt-0.5 text-xs text-muted">
                                {response.product_name ?? "No offer"}
                              </p>
                            </th>
                            <td className="px-3 py-3 text-right font-mono tabular-nums whitespace-nowrap">
                              {response.total_customer_price_cents != null
                                ? formatAudCents(
                                    response.total_customer_price_cents,
                                  )
                                : "—"}
                            </td>
                            <td className="px-3 py-3 text-right font-mono tabular-nums">
                              {response.buyer_utility != null
                                ? formatUtilityShort(response.buyer_utility)
                                : "—"}
                            </td>
                            <td className="px-3 py-3 text-right font-mono tabular-nums whitespace-nowrap">
                              {response.merchant_contribution_cents != null
                                ? formatAudCents(
                                    response.merchant_contribution_cents,
                                  )
                                : "—"}
                            </td>
                            <td
                              className={cn(
                                "px-3 py-3 text-xs",
                                selected
                                  ? "font-semibold text-mark"
                                  : valid
                                    ? "text-muted"
                                    : "text-warning",
                              )}
                            >
                              {selected
                                ? "✓ Buyer selected"
                                : valid
                                  ? "Not selected"
                                  : "No safe offer"}
                            </td>
                            <td className="py-3 text-right">
                              <button
                                type="button"
                                className="btn-quiet"
                                aria-label={`Inspect ${strategyTitle(response.strategy_name)} offer`}
                                onClick={() =>
                                  setStrategyInspect(response.strategy_name)
                                }
                              >
                                Inspect
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <div className="flex flex-wrap gap-x-5 gap-y-2">
                  <button
                    type="button"
                    className="btn-quiet"
                    onClick={() => setDetail("buyer")}
                  >
                    Buyer decision
                  </button>
                  <button
                    type="button"
                    className="btn-quiet"
                    onClick={() => setDetail("comparison")}
                  >
                    Merchant comparison
                  </button>
                  <button
                    type="button"
                    className="btn-quiet"
                    onClick={() => setDetail("semantic")}
                  >
                    Semantic Only vs AstraOS
                  </button>
                  <button
                    type="button"
                    className="btn-quiet"
                    onClick={() => setDetail("methodology")}
                  >
                    Methodology
                  </button>
                  <button
                    type="button"
                    className="btn-quiet ml-auto"
                    onClick={() => setInspect(true)}
                  >
                    Inspect experiment
                  </button>
                </div>
              </div>
            ) : mode === "benchmark" && benchmark ? (
              <div className="mt-4 space-y-3">
                <BenchmarkView benchmark={benchmark} />
                <div className="flex gap-4 text-xs">
                  <a
                    className="underline"
                    href={arenaBenchmarkExportUrl(
                      benchmark.benchmark_id,
                      "json",
                    )}
                  >
                    Export JSON
                  </a>
                  <a
                    className="underline"
                    href={arenaBenchmarkExportUrl(
                      benchmark.benchmark_id,
                      "csv",
                    )}
                  >
                    Export CSV
                  </a>
                </div>
              </div>
            ) : null}
          </AstraPanel>
        </div>
      ) : null}

      <Drawer
        open={Boolean(detail)}
        title={
          detail === "buyer"
            ? "Buyer decision"
            : detail === "comparison"
              ? "Merchant comparison"
              : detail === "semantic"
                ? "Semantic Only vs AstraOS"
                : "Evaluation methodology"
        }
        onClose={() => setDetail(null)}
      >
        {duel && detail === "buyer" ? (
          <div className="space-y-5">
            {highlights ? (
              <dl className="grid gap-2">
                <Highlight
                  label="Best buyer utility"
                  value={strategyTitle(highlights.bestUtility.strategy_name)}
                />
                <Highlight
                  label="Best merchant contribution"
                  value={strategyTitle(
                    highlights.bestContribution.strategy_name,
                  )}
                />
                <Highlight
                  label="Buyer selected"
                  value={
                    highlights.selected
                      ? strategyTitle(highlights.selected.strategy_name)
                      : "No purchase"
                  }
                />
              </dl>
            ) : null}
            <BuyerDecision duel={duel} />
          </div>
        ) : null}
        {duel && detail === "comparison" ? (
          <StrategyComparison duel={duel} />
        ) : null}
        {duel && detail === "semantic" ? (
          <SemanticOfferDelta duel={duel} />
        ) : null}
        {detail === "methodology" ? (
          <p className="text-sm leading-6 text-muted">
            Buyer selection uses a transparent simulated utility model with
            declared weights. Results are not observed real-world sales uplift.
            Policy-unsafe responses never enter buyer selection.
          </p>
        ) : null}
      </Drawer>
      <Drawer
        open={Boolean(strategyInspect)}
        title={
          strategyInspect ? strategyTitle(strategyInspect) : "Strategy offer"
        }
        onClose={() => setStrategyInspect(null)}
      >
        {duel?.strategies
          .filter((item) => item.response.strategy_name === strategyInspect)
          .map((item) => {
            const selected =
              !duel.buyer_selection.no_purchase &&
              duel.buyer_selection.selected_strategy ===
                item.response.strategy_name;
            return (
              <StrategyCard
                key={item.name}
                response={item.response}
                selected={selected}
                reference={defaultOffer ?? null}
                fitDelta={
                  selected && baseline
                    ? signedDelta(
                        (item.response.buyer_utility ?? 0) -
                          (baseline.buyer_utility ?? 0),
                      )
                    : undefined
                }
                contributionDelta={
                  selected && cheapest
                    ? moneyDelta(
                        (item.response.merchant_contribution_cents ?? 0) -
                          (cheapest.merchant_contribution_cents ?? 0),
                      )
                    : undefined
                }
              />
            );
          })}
      </Drawer>

      <ExperimentInspector
        open={inspect}
        duel={duel}
        onClose={() => setInspect(false)}
      />
    </div>
  );
}

function ModeTab({
  active,
  label,
  hint,
  onClick,
}: {
  active: boolean;
  label: string;
  hint: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "px-3 py-2 text-left text-sm",
        active
          ? "border-b-2 border-ink font-semibold text-ink"
          : "border-b-2 border-transparent text-muted hover:text-ink",
      )}
    >
      <span className="block">{label}</span>
      <span className="block text-[11px] font-normal text-muted">{hint}</span>
    </button>
  );
}

function Highlight({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-line px-3 py-2">
      <dt className="text-[11px] tracking-[0.06em] text-muted uppercase">
        {label}
      </dt>
      <dd className="mt-1 font-medium">{value}</dd>
    </div>
  );
}

function evaluationHighlights(duel: ArenaRunResponse) {
  const valid = validResponses(duel);
  if (!valid.length) return null;
  const bestUtility = [...valid].sort(
    (a, b) => (b.buyer_utility ?? 0) - (a.buyer_utility ?? 0),
  )[0];
  const bestContribution = [...valid].sort(
    (a, b) =>
      (b.merchant_contribution_cents ?? 0) -
      (a.merchant_contribution_cents ?? 0),
  )[0];
  return {
    bestUtility,
    bestContribution,
    selected: selectedStrategy(duel),
  };
}

function SemanticOfferDelta({ duel }: { duel: ArenaRunResponse }) {
  const semantic = findStrategy(duel, "SEMANTIC_ONLY");
  const astraos = findStrategy(duel, "ASTRAOS");
  if (!semantic || !astraos) return null;
  const sameProduct = semantic.sku === astraos.sku;
  const diffs = commercialDifference(semantic, astraos);
  const changed = diffs.filter((row) => row.changed);

  return (
    <div className="space-y-3 border-t border-line pt-5">
      <p className="text-xs tracking-[0.08em] text-muted">
        SEMANTIC ONLY VS ASTRAOS
      </p>
      <p className="text-sm font-medium">
        What whole-offer optimisation adds beyond semantic product matching
      </p>
      <p className="type-small text-muted">
        Semantic Only improves product matching with standard terms. AstraOS
        optimises the full offer vector.
        {sameProduct
          ? " Same product; commercial terms differ."
          : " Product selection also differs."}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        <OfferSnapshot title="Semantic Only" response={semantic} />
        <OfferSnapshot title="AstraOS" response={astraos} highlight />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] tracking-[0.06em] text-muted uppercase">
              <th className="py-2 font-medium">Field</th>
              <th className="py-2 font-medium">Semantic Only</th>
              <th className="py-2 font-medium">AstraOS</th>
              <th className="py-2 font-medium">Delta</th>
            </tr>
          </thead>
          <tbody>
            {diffs.map((row) => (
              <tr
                key={row.label}
                className={cn(
                  "border-b border-line",
                  row.changed && "bg-canvas",
                )}
              >
                <th className="py-2 font-medium text-muted">{row.label}</th>
                <td className="py-2">{row.from}</td>
                <td className={cn("py-2", row.changed && "font-medium")}>
                  {row.to}
                </td>
                <td className="py-2 font-mono text-xs tabular-nums">
                  {row.changed ? (row.delta ?? `${row.from} → ${row.to}`) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {changed.length === 0 ? (
        <p className="text-sm text-muted">
          No commercial field differences in this run.
        </p>
      ) : null}
    </div>
  );
}

function OfferSnapshot({
  title,
  response,
  highlight = false,
}: {
  title: string;
  response: NonNullable<ReturnType<typeof findStrategy>>;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "border px-3 py-3",
        highlight ? "border-ink bg-surface" : "border-line bg-canvas",
      )}
    >
      <p className="text-xs font-medium tracking-[0.06em]">{title}</p>
      <h3 className="mt-1 text-base font-semibold">
        {response.product_name ?? "No offer"}
      </h3>
      {response.sku ? (
        <p className="font-mono text-[11px] text-muted">{response.sku}</p>
      ) : null}
      <dl className="mt-2 space-y-1 text-sm">
        {response.total_customer_price_cents != null ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Customer total</dt>
            <dd className="font-mono tabular-nums">
              {formatAudCents(response.total_customer_price_cents)}
            </dd>
          </div>
        ) : null}
        {response.delivery != null || response.delivery_days != null ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Delivery</dt>
            <dd>{deliveryLabel(response.delivery, response.delivery_days)}</dd>
          </div>
        ) : null}
        {response.warranty != null || response.warranty_months != null ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Warranty</dt>
            <dd>
              {warrantyLabel(response.warranty, response.warranty_months)}
            </dd>
          </div>
        ) : null}
        {response.bundle != null || response.offer_id ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Bundle</dt>
            <dd>{bundleLabel(response.bundle)}</dd>
          </div>
        ) : null}
        {response.returns != null ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Returns</dt>
            <dd>{returnsLabel(response.returns)}</dd>
          </div>
        ) : null}
        {response.buyer_utility != null ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Buyer utility</dt>
            <dd className="font-mono tabular-nums">
              {formatUtilityShort(response.buyer_utility)}
            </dd>
          </div>
        ) : null}
        {response.merchant_contribution_cents != null ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Contribution</dt>
            <dd className="font-mono tabular-nums">
              {formatAudCents(response.merchant_contribution_cents)}
            </dd>
          </div>
        ) : null}
        {response.intervention_cost_cents != null ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Intervention</dt>
            <dd className="font-mono tabular-nums">
              {formatAudCents(response.intervention_cost_cents)}
            </dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}
