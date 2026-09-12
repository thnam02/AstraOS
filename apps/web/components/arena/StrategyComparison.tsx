import {
  comparisonRows,
  selectedStrategy,
  strongestBaseline,
  strategyTitle,
  tradeOffSummary,
} from "@/lib/arenaDisplay";
import type { ArenaRunResponse } from "@/types";

export function StrategyComparison({ duel }: { duel: ArenaRunResponse }) {
  const winner = selectedStrategy(duel);
  const baseline = strongestBaseline(duel);
  if (!winner || !baseline) return null;
  const rows = comparisonRows(baseline, winner);
  const summary = tradeOffSummary(winner, baseline);

  return (
    <section className="panel space-y-3">
      <p className="eyebrow">AstraOS vs strongest baseline</p>
      <h2 className="text-lg font-semibold tracking-tight">
        {strategyTitle(baseline.strategy_name)} · {strategyTitle(winner.strategy_name)}
      </h2>
      <div className="overflow-x-auto">
        <table className="table-dense w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-xs text-muted">
              <th className="py-2 font-medium"> </th>
              <th className="py-2 font-medium">
                {strategyTitle(baseline.strategy_name)}
              </th>
              <th className="py-2 font-medium">
                {strategyTitle(winner.strategy_name)}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-line">
                <th className="py-2 font-medium text-muted">{row.label}</th>
                <td className="py-2">{row.left}</td>
                <td className="py-2 font-medium">{row.right}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-sm">
        AstraOS gained {summary.fitDelta} buyer fit while preserving{" "}
        {summary.contributionDelta} merchant contribution relative to{" "}
        {summary.baselineName}.
      </p>
    </section>
  );
}
