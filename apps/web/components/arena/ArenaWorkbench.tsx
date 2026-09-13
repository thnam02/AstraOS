"use client";

import { useEffect, useState } from "react";

import { BenchmarkView } from "@/components/arena/BenchmarkView";
import { BuyerDecision } from "@/components/arena/BuyerDecision";
import { ExperimentInspector } from "@/components/arena/ExperimentInspector";
import { StrategyCard } from "@/components/arena/StrategyCard";
import { StrategyComparison } from "@/components/arena/StrategyComparison";
import { AstraCallout } from "@/components/astra";
import { Disclosure } from "@/components/shared/Disclosure";
import { ErrorState } from "@/components/shared/EmptyState";
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
  moneyDelta,
  qualitativePriorities,
  selectedStrategy,
  signedDelta,
  strongestBaseline,
  validResponses,
  warrantyLabel,
} from "@/lib/arenaDisplay";
import { formatAudCents } from "@/lib/money";
import type {
  ArenaBenchmarkResponse,
  ArenaRunResponse,
  BuyerProfile,
} from "@/types";

const ABLATION_STRATEGIES = [
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
    label: "Urgent travel",
    title: "Urgent traveller",
    profile: "URGENT_TRAVELLER" as BuyerProfile,
    intent: ARENA_HERO,
  },
  {
    id: "budget",
    label: "Budget",
    title: "Budget shopper",
    profile: "BUDGET_SHOPPER" as BuyerProfile,
    intent:
      "I need wireless ANC headphones under A$260. Cheapest option that still works is fine. Two-day delivery is ok.",
  },
  {
    id: "assurance",
    label: "Assurance",
    title: "Assurance",
    profile: "ASSURANCE_BUYER" as BuyerProfile,
    intent:
      "I want reliable ANC headphones under A$350. A long warranty matters more than getting the cheapest pair.",
  },
] as const;

export function ArenaWorkbench() {
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
  const [benchmark, setBenchmark] = useState<ArenaBenchmarkResponse | null>(null);
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
        setError(err instanceof Error ? err.message : "Unable to load benchmark");
      });
  }, []);

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
            : [...ABLATION_STRATEGIES],
        }),
      );
    } catch (err) {
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
    } catch (err) {
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1">
          <button
            type="button"
            className={`rounded-[6px] px-3 py-1.5 text-xs tracking-[0.06em] ${
              mode === "duel" ? "bg-ink text-surface" : "btn-ghost"
            }`}
            onClick={() => setMode("duel")}
          >
            LIVE DUEL
          </button>
          <button
            type="button"
            className={`rounded-[6px] px-3 py-1.5 text-xs tracking-[0.06em] ${
              mode === "benchmark" ? "bg-ink text-surface" : "btn-ghost"
            }`}
            onClick={() => setMode("benchmark")}
          >
            BENCHMARK
          </button>
        </div>
        <AstraCallout title="Synthetic evaluation">
          Buyer selection uses a transparent simulated utility model. Results
          are not observed real-world sales uplift.
        </AstraCallout>
      </div>

      {mode === "duel" ? (
        <div className="space-y-4">
          <section className="panel space-y-3">
            <p className="text-sm text-muted">
              Controlled experiment. Same buyer, catalogue, inventory, policy,
              and buyer model. Only merchant strategy changes: Default → Discount
              → Semantic Only → AstraOS.
            </p>
            <div className="flex flex-wrap items-end gap-3">
              <label className="text-xs text-muted">
                Scenario
                <select
                  className="control mt-1 block px-2 py-1 text-sm"
                  value={scenario}
                  onChange={(event) => applyPreset(event.target.value)}
                >
                  {PRESETS.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                  <option value="custom">Custom request</option>
                </select>
              </label>
              <label className="text-xs text-muted">
                Buyer profile
                <select
                  className="control mt-1 block px-2 py-1 text-sm"
                  value={profile}
                  onChange={(event) =>
                    setProfile(event.target.value as BuyerProfile)
                  }
                >
                  <option value="URGENT_TRAVELLER">Urgent traveller</option>
                  <option value="BUDGET_SHOPPER">Budget shopper</option>
                  <option value="ASSURANCE_BUYER">Assurance</option>
                  <option value="QUALITY_FIRST">Quality first</option>
                  <option value="BALANCED">Balanced</option>
                  <option value="INTENT_ADAPTED">Intent-adapted</option>
                </select>
              </label>
              <div className="flex gap-1">
                {PRESETS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={
                      scenario === item.id ? "btn-primary" : "btn-ghost"
                    }
                    onClick={() => applyPreset(item.id)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <label className="flex items-center gap-2 text-xs text-muted">
                <input
                  type="checkbox"
                  checked={moreStrategies}
                  onChange={(event) => setMoreStrategies(event.target.checked)}
                />
                More strategies
              </label>
              <button
                type="button"
                className="btn-primary"
                onClick={() => void onDuel()}
                disabled={busy}
              >
                {busy ? "Running…" : "Run duel"}
              </button>
            </div>
          </section>

          <section className="panel">
            <p className="eyebrow">Buyer mission</p>
            {custom || editing ? (
              <textarea
                className="control mt-2 h-24 w-full p-3 text-sm"
                value={intent}
                onChange={(event) => {
                  setIntent(event.target.value);
                  setScenario("custom");
                }}
              />
            ) : (
              <div className="mt-2 grid gap-4 md:grid-cols-[minmax(0,1.4fr)_220px]">
                <div>
                  <h2 className="text-lg font-semibold tracking-tight">
                    {preset?.title ?? "Mission"}
                  </h2>
                  <p className="mt-2 text-sm leading-6">“{intent}”</p>
                  <button
                    type="button"
                    className="mt-2 text-xs text-muted underline"
                    onClick={() => setEditing(true)}
                  >
                    Edit mission
                  </button>
                </div>
                <dl className="space-y-1 text-sm">
                  <dt className="eyebrow">Buyer priorities</dt>
                  {qualitativePriorities(profile).map((item) => (
                    <div key={item.label} className="flex justify-between gap-3">
                      <dt>{item.label}</dt>
                      <dd className="text-muted">{item.level}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </section>

          {duel ? (
            <div className="space-y-4">
              <div className="border border-line bg-canvas px-4 py-3">
                <p className="eyebrow">Controlled experiment</p>
                <p className="mt-1 text-sm">
                  Same buyer · same merchant · same rules. Only strategy differs.
                </p>
              </div>

              {summary ? (
                <section className="panel">
                  <p className="eyebrow">Result</p>
                  <h2 className="mt-1 text-xl font-semibold tracking-tight">
                    {summary.title}
                  </h2>
                  {winner ? (
                    <dl className="mt-3 flex flex-wrap gap-6 text-sm">
                      <div>
                        <dt className="text-muted">Buyer fit</dt>
                        <dd className="font-mono text-2xl font-semibold tabular-nums">
                          {winner.buyer_utility?.toFixed(2)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-muted">Merchant contribution</dt>
                        <dd className="font-mono text-2xl font-semibold tabular-nums">
                          {formatAudCents(
                            winner.merchant_contribution_cents ?? 0,
                          )}
                        </dd>
                      </div>
                    </dl>
                  ) : null}
                  <p className="mt-2 text-sm text-muted">{summary.body}</p>
                </section>
              ) : null}

              <div>
                <p className="eyebrow mb-2">Strategy duel</p>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {duel.strategies.map((item) => {
                    const selected =
                      !duel.buyer_selection.no_purchase &&
                      duel.buyer_selection.selected_strategy ===
                        item.response.strategy_name;
                    const nextBest = baseline;
                    return (
                      <StrategyCard
                        key={item.name}
                        response={item.response}
                        selected={selected}
                        reference={defaultOffer ?? null}
                        fitDelta={
                          selected && nextBest
                            ? signedDelta(
                                (item.response.buyer_utility ?? 0) -
                                  (nextBest.buyer_utility ?? 0),
                              )
                            : undefined
                        }
                        contributionDelta={
                          selected && cheapest
                            ? moneyDelta(
                                (item.response.merchant_contribution_cents ??
                                  0) -
                                  (cheapest.merchant_contribution_cents ?? 0),
                              )
                            : undefined
                        }
                      />
                    );
                  })}
                </div>
              </div>

              <SemanticOfferDelta duel={duel} />

              <div className="grid gap-4 xl:grid-cols-2">
                <BuyerDecision duel={duel} />
                <StrategyComparison duel={duel} />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => setInspect(true)}
                >
                  Inspect experiment
                </button>
                <Disclosure title="How simulation works">
                  <p className="text-sm text-muted">
                    Buyer selection uses a transparent simulated utility model
                    with declared weights. Results are not observed real-world
                    sales uplift. Policy-unsafe responses never enter buyer
                    selection.
                  </p>
                </Disclosure>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">
              Run a duel to compare Default, Always Discount, Semantic Only, and
              AstraOS against the same merchant state.
            </p>
          )}
        </div>
      ) : (
        <section className="panel space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-muted">
              Missions
              <input
                className="control mt-1 block w-24 px-2 py-1"
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
                className="control mt-1 block w-24 px-2 py-1"
                type="number"
                value={seed}
                onChange={(event) => setSeed(Number(event.target.value))}
              />
            </label>
            <button
              type="button"
              className="btn-primary"
              onClick={() => void onBenchmark()}
              disabled={busy}
            >
              {busy ? "Running…" : "Rerun benchmark"}
            </button>
          </div>
          <p className="text-xs text-muted">
            Latest completed run loads automatically. Same seed reproduces the
            same ranking.
          </p>
          {benchmark ? (
            <>
              <BenchmarkView benchmark={benchmark} />
              <div className="flex gap-3 text-xs">
                <a
                  className="underline"
                  href={arenaBenchmarkExportUrl(benchmark.benchmark_id, "json")}
                >
                  Export JSON
                </a>
                <a
                  className="underline"
                  href={arenaBenchmarkExportUrl(benchmark.benchmark_id, "csv")}
                >
                  Export CSV
                </a>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted">
              No precomputed benchmark is loaded. Run a reproducible seed-2026
              benchmark to populate this panel.
            </p>
          )}
        </section>
      )}

      {error ? <ErrorState message={error} /> : null}
      <ExperimentInspector
        open={inspect}
        duel={duel}
        onClose={() => setInspect(false)}
      />
    </div>
  );
}

function SemanticOfferDelta({ duel }: { duel: ArenaRunResponse }) {
  const semantic = findStrategy(duel, "SEMANTIC_ONLY");
  const astraos = findStrategy(duel, "ASTRAOS");
  if (!semantic || !astraos) return null;
  const sameProduct = semantic.sku === astraos.sku;
  return (
    <section className="panel space-y-3">
      <p className="eyebrow">What changed · Semantic Only vs AstraOS</p>
      <p className="text-xs text-muted">
        Semantic search finds a product. AstraOS builds the commercial response.
        {sameProduct ? " Same product; offer terms differ." : " Product also changed."}
      </p>
      <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-start">
        <OfferSnapshot title="Semantic Only" response={semantic} />
        <p className="self-center text-center text-xs text-muted">↓</p>
        <OfferSnapshot title="AstraOS" response={astraos} />
      </div>
      <div>
        <p className="eyebrow">Commercial difference</p>
        <ul className="mt-2 space-y-1 text-sm">
          {commercialDifference(semantic, astraos)
            .filter((row) => row.changed)
            .map((row) => (
              <li key={row.label} className="flex justify-between gap-3">
                <span className="text-muted">{row.label}</span>
                <span>
                  {row.from} → {row.to}
                </span>
              </li>
            ))}
        </ul>
        <p className="mt-2 font-mono text-xs tabular-nums text-muted">
          Buyer utility{" "}
          {signedDelta((astraos.buyer_utility ?? 0) - (semantic.buyer_utility ?? 0))}
          {" · "}
          Contribution{" "}
          {moneyDelta(
            (astraos.merchant_contribution_cents ?? 0) -
              (semantic.merchant_contribution_cents ?? 0),
          )}
        </p>
      </div>
    </section>
  );
}

function OfferSnapshot({
  title,
  response,
}: {
  title: string;
  response: NonNullable<ReturnType<typeof findStrategy>>;
}) {
  return (
    <div>
      <p className="text-xs font-medium tracking-[0.06em]">{title}</p>
      <h3 className="mt-1 text-base font-semibold">
        {response.product_name ?? "No offer"}
      </h3>
      <p className="font-mono text-sm tabular-nums">
        {response.total_customer_price_cents != null
          ? formatAudCents(response.total_customer_price_cents)
          : "—"}
      </p>
      <ul className="mt-2 space-y-0.5 text-sm text-muted">
        <li>{deliveryLabel(response.delivery, response.delivery_days)}</li>
        <li>{warrantyLabel(response.warranty, response.warranty_months)}</li>
        <li>{bundleLabel(response.bundle)}</li>
      </ul>
    </div>
  );
}
