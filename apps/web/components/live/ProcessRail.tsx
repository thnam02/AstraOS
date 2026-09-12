export type LiveStage =
  | "understand"
  | "qualify"
  | "match"
  | "construct"
  | "optimise"
  | "negotiate"
  | "transact"
  | "learn";

export const LIVE_STAGES: LiveStage[] = [
  "understand",
  "qualify",
  "match",
  "construct",
  "optimise",
  "negotiate",
  "transact",
  "learn",
];

export type RailState = "complete" | "active" | "future" | "failed";

export function processRailState(
  id: LiveStage,
  flags: {
    hasMatch: boolean;
    hasOffers: boolean;
    hasOpt: boolean;
    hasNego: boolean;
    hasTxn: boolean;
    txnFailed: boolean;
    txnComplete: boolean;
  },
  active: LiveStage,
): RailState {
  if (flags.txnFailed && id === "transact") return "failed";
  if (id === active) return "active";
  if (!flags.hasMatch) return "future";
  const order = LIVE_STAGES.indexOf(id);
  const current = LIVE_STAGES.indexOf(active);
  if (order < current) return "complete";
  if (id === "understand" || id === "qualify" || id === "match") return "complete";
  if (id === "construct") return flags.hasOffers ? "complete" : "future";
  if (id === "optimise") return flags.hasOpt ? "complete" : "future";
  if (id === "negotiate") return flags.hasNego ? "complete" : "future";
  if (id === "transact") {
    if (flags.txnComplete) return "complete";
    return "future";
  }
  return flags.txnComplete ? "complete" : "future";
}

export function ProcessRail({
  active,
  flags,
  onSelect,
}: {
  active: LiveStage;
  flags: Omit<Parameters<typeof processRailState>[1], never>;
  onSelect: (stage: LiveStage) => void;
}) {
  return (
    <ol
      className="flex flex-wrap items-center gap-x-1 gap-y-1"
      aria-label="Decision pipeline"
    >
      {LIVE_STAGES.map((id, index) => {
        const state = processRailState(id, flags, active);
        const mark =
          state === "complete" ? "✓" : state === "active" ? "●" : state === "failed" ? "!" : "○";
        return (
          <li key={id} className="flex items-center">
            {index > 0 ? (
              <span className="mx-1 text-[10px] text-line" aria-hidden>
                ─
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => onSelect(id)}
              aria-current={state === "active" ? "step" : undefined}
              className={`text-[11px] uppercase tracking-[0.08em] ${
                state === "active"
                  ? "font-semibold text-ink"
                  : state === "complete"
                    ? "text-ink"
                    : state === "failed"
                      ? "text-danger"
                      : "text-muted"
              }`}
            >
              <span className="mr-1" aria-hidden>
                {mark}
              </span>
              {id}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
