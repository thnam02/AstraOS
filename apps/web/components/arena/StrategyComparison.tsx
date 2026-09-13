import {
  comparisonRows,
  findStrategy,
  merchantEconomicsLine,
  selectedStrategy,
  strongestBaseline,
  strategyTitle,
} from "@/lib/arenaDisplay";
import type { ArenaRunResponse } from "@/types";

export function StrategyComparison({ duel }: { duel: ArenaRunResponse }) {
  const winner = selectedStrategy(duel);
  const semantic = findStrategy(duel, "SEMANTIC_ONLY");
  const comparingSemantic =
    winner?.strategy_name === "ASTRAOS" && Boolean(semantic?.offer_id);
  const baseline =
    comparingSemantic && semantic
      ? semantic
      : strongestBaseline(duel);
  if (!winner || !baseline) return null;
  const rows = comparisonRows(baseline, winner);

  return (
    <section className="space-y-3">
      <p className="eyebrow">
        {comparingSemantic
          ? "Semantic Only vs AstraOS"
          : "Merchant result"}
      </p>
      <h2 className="text-lg font-semibold tracking-tight">
        {strategyTitle(baseline.strategy_name)} · {strategyTitle(winner.strategy_name)}
      </h2>
      {comparingSemantic ? (
        <p className="text-xs text-muted">
          Same controlled experiment. Semantic Only improves product matching;
          AstraOS optimises the full commercial offer.
        </p>
      ) : null}
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
            {rows.map((row) => {
              const changed = row.left !== row.right;
              return (
                <tr key={row.label} className="border-b border-line">
                  <th className="py-2 font-medium text-muted">{row.label}</th>
                  <td className="py-2">{row.left}</td>
                  <td className={`py-2 ${changed ? "font-medium" : ""}`}>
                    {row.right}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-sm">{merchantEconomicsLine(winner, baseline)}</p>
    </section>
  );
}
