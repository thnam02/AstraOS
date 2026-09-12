"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { strategyTitle } from "@/lib/arenaDisplay";
import { formatAudCents } from "@/lib/money";
import type { ArenaBenchmarkResponse } from "@/types";

const HERO_SEGMENTS = ["budget", "urgent", "assurance", "balanced"] as const;

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function BenchmarkView({
  benchmark,
}: {
  benchmark: ArenaBenchmarkResponse;
}) {
  const chart = useMemo(
    () =>
      benchmark.strategy_metrics.map((row) => ({
        name: strategyTitle(row.strategy_name),
        x: row.selection_rate * 100,
        y: row.contribution_per_opportunity_cents / 100,
      })),
    [benchmark],
  );

  const astra = benchmark.strategy_metrics.find(
    (row) => row.strategy_name === "ASTRAOS",
  );

  return (
    <div className="space-y-5">
      <p className="text-sm">
        Across this {benchmark.mission_count}-mission synthetic benchmark, AstraOS
        was selected in {pct(astra?.selection_rate ?? 0)} of simulated missions
        under the declared buyer utility model.
      </p>

      <div className="h-[300px] border border-line bg-surface px-3 py-3">
        <p className="mb-2 text-xs text-muted">
          Simulated selection rate vs contribution per opportunity. Top-right is
          stronger buyer/merchant trade-off.
        </p>
        <ResponsiveContainer width="100%" height="88%">
          <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="#dddad2" />
            <XAxis
              type="number"
              dataKey="x"
              name="Selection"
              unit="%"
              tick={{ fontSize: 11, fill: "#5c5a54" }}
              label={{
                value: "Simulated selection rate (%)",
                position: "insideBottom",
                offset: -2,
                fontSize: 11,
                fill: "#5c5a54",
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Contribution"
              tick={{ fontSize: 11, fill: "#5c5a54" }}
              label={{
                value: "Contribution / opportunity (A$)",
                angle: -90,
                position: "insideLeft",
                fontSize: 11,
                fill: "#5c5a54",
              }}
            />
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
                    <p>Contribution / opp. A${point.y.toFixed(2)}</p>
                  </div>
                );
              }}
            />
            <Scatter data={chart} fill="#141413" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {chart.map((point) => (
          <li key={point.name}>
            {point.name}: {point.x.toFixed(1)}% · A${point.y.toFixed(2)}
          </li>
        ))}
      </ul>

      <div className="overflow-x-auto">
        <table className="table-dense w-full text-left text-xs">
          <thead>
            <tr className="border-b border-line text-muted">
              <th className="py-2 font-medium">Strategy</th>
              <th className="py-2 font-medium">Selection</th>
              <th className="py-2 font-medium">Contribution / opportunity</th>
              <th className="py-2 font-medium">Avg intervention</th>
              <th className="py-2 font-medium">No offer</th>
            </tr>
          </thead>
          <tbody>
            {benchmark.strategy_metrics.map((row) => (
              <tr key={row.strategy_name} className="border-b border-line">
                <td className="py-2 font-medium">
                  {strategyTitle(row.strategy_name)}
                </td>
                <td>{pct(row.selection_rate)}</td>
                <td>
                  {formatAudCents(row.contribution_per_opportunity_cents)}
                </td>
                <td>{formatAudCents(row.avg_intervention_cost_cents ?? 0)}</td>
                <td>{pct(row.no_offer_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div>
        <p className="eyebrow">Performance by buyer type</p>
        <p className="mt-1 text-xs text-muted">
          Selection rate by scenario. AstraOS is adaptive, not a hardcoded winner.
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="table-dense w-full text-left text-xs">
            <thead>
              <tr className="border-b border-line text-muted">
                <th className="py-2 font-medium">Segment</th>
                {benchmark.strategies.map((name) => (
                  <th key={name} className="py-2 font-medium">
                    {strategyTitle(name)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {HERO_SEGMENTS.map((tag) => (
                <tr key={tag} className="border-b border-line">
                  <td className="py-2 capitalize">{tag}</td>
                  {benchmark.strategies.map((name) => {
                    const row = benchmark.segment_metrics.find(
                      (item) =>
                        item.scenario_tag === tag &&
                        item.strategy_name === name,
                    );
                    const rate = row?.selection_rate ?? 0;
                    return (
                      <td
                        key={name}
                        className={rate >= 0.5 ? "font-medium" : "text-muted"}
                      >
                        {row ? pct(rate) : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
