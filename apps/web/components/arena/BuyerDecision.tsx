import {
  componentNote,
  primaryDecisionSentence,
  profileLabel,
  selectedStrategy,
  strongestBaseline,
  weightRows,
  winnerReasons,
} from "@/lib/arenaDisplay";
import type { ArenaRunResponse } from "@/types";

export function BuyerDecision({ duel }: { duel: ArenaRunResponse }) {
  const winner = selectedStrategy(duel);
  const baseline = strongestBaseline(duel);
  const weights = weightRows(duel.explanation.weights);

  if (duel.buyer_selection.no_purchase) {
    return (
      <section className="panel space-y-3">
        <p className="eyebrow">Simulated buyer decision</p>
        <h2 className="text-xl font-semibold tracking-tight">No purchase</h2>
        <p className="text-sm text-muted">
          {primaryDecisionSentence(duel)}
        </p>
      </section>
    );
  }

  return (
    <section className="panel space-y-4">
      <div>
        <p className="eyebrow">Simulated buyer decision</p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight">
          {winner ? `${winner.product_name} selected` : "Selected"}
        </h2>
        <p className="mt-1 text-sm text-muted">
          Buyer profile: {profileLabel(duel.buyer_profile)}
        </p>
      </div>
      <div>
        <p className="eyebrow">Buyer priorities</p>
        <ul className="mt-2 space-y-1.5">
          {weights.map((row) => (
            <li key={row.key} className="grid grid-cols-[120px_40px_1fr_auto] items-center gap-2 text-xs">
              <span>{row.label}</span>
              <span className="font-mono tabular-nums text-muted">{row.pct}%</span>
              <span className="h-1.5 bg-line">
                <span
                  className="block h-full bg-ink"
                  style={{ width: `${row.pct}%` }}
                />
              </span>
              <span className="text-muted">
                {componentNote(row.key, winner, baseline)}
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <p className="eyebrow">Why it won</p>
        <ul className="mt-2 space-y-1 text-sm">
          {winnerReasons(duel).map((line) => (
            <li key={line} className="flex gap-2">
              <span className="text-success">✓</span>
              <span>{line}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-sm text-muted">{primaryDecisionSentence(duel)}</p>
      </div>
    </section>
  );
}
