"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  arenaBenchmarkExportUrl,
  createArenaBenchmark,
  getArenaBenchmark,
  getLatestArenaBenchmark,
  runArenaDuel,
} from "@/lib/api";
import { formatAudCents, formatRate } from "@/lib/money";
import type {
  ArenaBenchmarkResponse,
  ArenaRunResponse,
  ArenaStrategyResponse,
  BuyerProfile,
} from "@/types";

const ARENA_HERO =
  "I need ANC headphones under A$350 for a long-haul flight. Delivered today. Comfort and reliability matter more than getting the cheapest option.";

const PRESETS = [
  {
    id: "urgent",
    label: "Urgent travel",
    profile: "URGENT_TRAVELLER" as BuyerProfile,
    intent: ARENA_HERO,
  },
  {
    id: "budget",
    label: "Budget",
    profile: "BUDGET_SHOPPER" as BuyerProfile,
    intent:
      "I need wireless ANC headphones under A$260. Cheapest option that still works is fine. Two-day delivery is ok.",
  },
  {
    id: "assurance",
    label: "Assurance",
    profile: "ASSURANCE_BUYER" as BuyerProfile,
    intent:
      "I want reliable ANC headphones under A$350. A long warranty matters more than getting the cheapest pair.",
  },
];

const DISCLAIMER =
  "Synthetic evaluation using transparent simulated buyer utility. Results do not represent observed real-world conversion uplift.";

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function Card({
  response,
  selected,
}: {
  response: ArenaStrategyResponse;
  selected: boolean;
}) {
  return (
    <article
      className={`border bg-surface p-4 ${
        selected ? "border-ink" : "border-line"
      }`}
    >
      <div className="flex items-center justify-between">
        <p className="text-xs tracking-[0.14em] text-muted">
          {response.strategy_name.replaceAll("_", " ")}
        </p>
        {selected ? (
          <span className="text-xs text-success">SELECTED</span>
        ) : null}
      </div>
      {response.offer_id ? (
        <>
          <h3 className="mt-2 text-sm font-semibold">{response.product_name}</h3>
          <p className="text-xs text-muted">{response.sku}</p>
          <p className="mt-3 text-lg font-semibold">
            {formatAudCents(response.total_customer_price_cents ?? 0)}
          </p>
          <p className="mt-1 text-sm text-muted">
            {response.delivery} · {response.warranty}
            {response.bundle ? ` · ${response.bundle}` : ""}
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div>
              <dt className="text-muted">Buyer utility</dt>
              <dd className="font-medium">
                {response.buyer_utility?.toFixed(2) ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Contribution</dt>
              <dd className="font-medium">
                {formatAudCents(response.merchant_contribution_cents ?? 0)}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Intervention</dt>
              <dd>
                {formatAudCents(response.intervention_cost_cents ?? 0)}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Policy</dt>
              <dd>{response.policy_safe ? "safe" : "blocked"}</dd>
            </div>
          </dl>
        </>
      ) : (
        <p className="mt-3 text-sm text-muted">
          {response.failure_reason ?? "No offer"}
        </p>
      )}
    </article>
  );
}

export function ArenaWorkbench() {
  const [mode, setMode] = useState<"duel" | "benchmark">("duel");
  const [intent, setIntent] = useState(ARENA_HERO);
  const [profile, setProfile] = useState<BuyerProfile>("URGENT_TRAVELLER");
  const [duel, setDuel] = useState<ArenaRunResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [missionCount, setMissionCount] = useState(100);
  const [seed, setSeed] = useState(2026);
  const [benchmark, setBenchmark] = useState<ArenaBenchmarkResponse | null>(null);

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
      setDuel(await runArenaDuel({ intent, buyer_profile: profile }));
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

  const chart = useMemo(
    () =>
      (benchmark?.strategy_metrics ?? []).map((row) => ({
        name: row.strategy_name,
        x: row.selection_rate * 100,
        y: row.contribution_per_opportunity_cents / 100,
      })),
    [benchmark],
  );

  const heroSegments = ["budget", "urgent", "assurance", "balanced"];

  return (
    <div className="space-y-6">
      <p className="border border-warning/30 bg-warning/5 px-3 py-2 text-xs text-warning">
        {DISCLAIMER}
      </p>
      <div className="flex gap-3 text-xs tracking-[0.14em]">
        <button
          type="button"
          className={mode === "duel" ? "text-ink" : "text-muted"}
          onClick={() => setMode("duel")}
        >
          LIVE DUEL
        </button>
        <button
          type="button"
          className={mode === "benchmark" ? "text-ink" : "text-muted"}
          onClick={() => setMode("benchmark")}
        >
          BENCHMARK
        </button>
      </div>

      {mode === "duel" ? (
        <section className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((item) => (
              <button
                key={item.id}
                type="button"
                className="border border-line px-3 py-1 text-xs"
                onClick={() => {
                  setIntent(item.intent);
                  setProfile(item.profile);
                }}
              >
                {item.label}
              </button>
            ))}
          </div>
          <textarea
            className="h-28 w-full border border-line bg-surface p-3 text-sm"
            value={intent}
            onChange={(event) => setIntent(event.target.value)}
          />
          <div className="flex flex-wrap items-center gap-3">
            <select
              className="border border-line bg-surface px-2 py-1 text-sm"
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
            <button
              type="button"
              className="border border-ink bg-ink px-3 py-1 text-xs text-surface"
              onClick={() => void onDuel()}
              disabled={busy}
            >
              {busy ? "Running…" : "Run duel"}
            </button>
          </div>
          {duel ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {duel.strategies.map((item) => (
                  <Card
                    key={item.name}
                    response={item.response}
                    selected={
                      !duel.buyer_selection.no_purchase &&
                      duel.buyer_selection.selected_strategy === item.name
                    }
                  />
                ))}
              </div>
              <div className="border border-line bg-surface p-4">
                <p className="text-xs tracking-[0.14em] text-muted">
                  SIMULATED BUYER SELECTS
                </p>
                <p className="mt-1 text-lg font-semibold">
                  {duel.buyer_selection.no_purchase
                    ? "NO PURCHASE"
                    : duel.buyer_selection.selected_strategy}
                </p>
                {duel.buyer_selection.simulated_utility != null ? (
                  <p className="text-sm text-muted">
                    Utility {duel.buyer_selection.simulated_utility.toFixed(2)}
                  </p>
                ) : null}
                {duel.explanation.weights ? (
                  <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs md:grid-cols-3">
                    {Object.entries(duel.explanation.weights).map(
                      ([key, value]) => (
                        <div key={key}>
                          <dt className="text-muted">{key}</dt>
                          <dd>{formatRate(value)}</dd>
                        </div>
                      ),
                    )}
                  </dl>
                ) : null}
                <ul className="mt-3 list-disc space-y-1 pl-4 text-sm text-muted">
                  {(duel.explanation.reasons ?? []).map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
              <p className="text-xs text-muted">{duel.disclaimer}</p>
            </div>
          ) : null}
        </section>
      ) : (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-xs text-muted">
              Missions
              <input
                className="ml-2 w-24 border border-line px-2 py-1"
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
                className="ml-2 w-24 border border-line px-2 py-1"
                type="number"
                value={seed}
                onChange={(event) => setSeed(Number(event.target.value))}
              />
            </label>
            <button
              type="button"
              className="border border-ink bg-ink px-3 py-1 text-xs text-surface"
              onClick={() => void onBenchmark()}
              disabled={busy}
            >
              {busy ? "Running…" : "Rerun benchmark"}
            </button>
          </div>
          <p className="text-xs text-muted">
            Latest completed run loads automatically when available. Same seed
            reproduces the same ranking. This is a synthetic evaluation.
          </p>
          {!benchmark && !busy ? (
            <p className="text-sm text-muted">
              No precomputed benchmark is loaded. Run a reproducible seed-2026
              benchmark to populate this panel.
            </p>
          ) : null}
          {benchmark ? (
            <div className="space-y-6">
              <p className="text-sm">
                In this {benchmark.mission_count}-mission synthetic benchmark,
                AstraOS was selected in{" "}
                {pct(
                  benchmark.strategy_metrics.find(
                    (row) => row.strategy_name === "ASTRAOS",
                  )?.selection_rate ?? 0,
                )}{" "}
                of simulated missions under the declared buyer utility model.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-line text-muted">
                      <th className="py-2">Strategy</th>
                      <th>Selection</th>
                      <th>Contribution / opp.</th>
                      <th>Avg intervention</th>
                      <th>No offer</th>
                      <th>Violations</th>
                    </tr>
                  </thead>
                  <tbody>
                    {benchmark.strategy_metrics.map((row) => (
                      <tr key={row.strategy_name} className="border-b border-line">
                        <td className="py-2 font-medium">{row.strategy_name}</td>
                        <td>{pct(row.selection_rate)}</td>
                        <td>
                          {formatAudCents(row.contribution_per_opportunity_cents)}
                        </td>
                        <td>
                          {formatAudCents(row.avg_intervention_cost_cents ?? 0)}
                        </td>
                        <td>{pct(row.no_offer_rate)}</td>
                        <td>
                          {pct(
                            row.policy_violation_rate +
                              row.hard_constraint_violation_rate,
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="h-[280px] border border-line bg-surface p-3">
                <p className="mb-2 text-xs text-muted">
                  Selection rate vs contribution per opportunity. Top-right is
                  better.
                </p>
                <ResponsiveContainer width="100%" height="90%">
                  <ScatterChart>
                    <CartesianGrid stroke="#e4e4e0" />
                    <XAxis
                      type="number"
                      dataKey="x"
                      name="Selection %"
                      unit="%"
                    />
                    <YAxis type="number" dataKey="y" name="Contribution" />
                    <Tooltip
                      content={({ payload }) => {
                        const point = payload?.[0]?.payload as
                          | { name: string; x: number; y: number }
                          | undefined;
                        if (!point) return null;
                        return (
                          <div className="border border-line bg-surface px-3 py-2 text-xs">
                            <p className="font-medium">{point.name}</p>
                            <p>Selection {point.x.toFixed(1)}%</p>
                            <p>Contribution / opp. {point.y.toFixed(2)}</p>
                          </div>
                        );
                      }}
                    />
                    <Scatter data={chart} fill="#171717" />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-line text-muted">
                      <th className="py-2">Segment</th>
                      {benchmark.strategies.map((name) => (
                        <th key={name}>{name}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {heroSegments.map((tag) => (
                      <tr key={tag} className="border-b border-line">
                        <td className="py-2 capitalize">{tag}</td>
                        {benchmark.strategies.map((name) => {
                          const row = benchmark.segment_metrics.find(
                            (item) =>
                              item.scenario_tag === tag &&
                              item.strategy_name === name,
                          );
                          return (
                            <td key={name}>
                              {row ? pct(row.selection_rate) : "—"}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
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
              <p className="text-xs text-muted">{benchmark.disclaimer}</p>
            </div>
          ) : null}
        </section>
      )}
      {error ? <p className="text-sm text-danger">{error}</p> : null}
    </div>
  );
}
