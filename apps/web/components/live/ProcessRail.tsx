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

export type RailState = "complete" | "active" | "future" | "failed" | "blocked";

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

const STAGE_COPY: Record<LiveStage, string> = {
  understand: "Understand",
  qualify: "Qualify",
  match: "Match",
  construct: "Construct",
  optimise: "Optimise",
  negotiate: "Negotiate",
  transact: "Transact",
  learn: "Learn",
};

export function ProcessRail({
  active,
  flags,
  onSelect,
  interactive = true,
}: {
  active: LiveStage;
  flags: Omit<Parameters<typeof processRailState>[1], never>;
  onSelect?: (stage: LiveStage) => void;
  interactive?: boolean;
}) {
  return (
    <ol
      className="flex flex-wrap items-center gap-x-0.5 gap-y-1"
      aria-label="Decision pipeline"
    >
      {LIVE_STAGES.map((id, index) => {
        const state = processRailState(id, flags, active);
        const mark =
          state === "complete"
            ? "✓"
            : state === "active"
              ? "●"
              : state === "failed" || state === "blocked"
                ? "!"
                : "○";
        return (
          <li key={id} className="flex items-center">
            {index > 0 ? (
              <span
                className={`mx-1.5 text-[10px] motion-safe:transition-colors ${
                  state === "future" ? "text-line-muted" : "text-line"
                }`}
                aria-hidden
              >
                ──
              </span>
            ) : null}
            {interactive && onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(id)}
                aria-current={state === "active" ? "step" : undefined}
                aria-label={`${STAGE_COPY[id]}, ${state}`}
                className={`cursor-pointer text-[11px] uppercase tracking-[0.08em] motion-safe:transition-colors ${
                  state === "active"
                    ? "font-semibold text-ink"
                    : state === "complete"
                      ? "text-ink"
                      : state === "failed" || state === "blocked"
                        ? "text-danger"
                        : "text-muted"
                }`}
              >
                <span className="mr-1" aria-hidden>
                  {mark}
                </span>
                {STAGE_COPY[id]}
              </button>
            ) : (
              <span
                aria-current={state === "active" ? "step" : undefined}
                className={`text-[11px] uppercase tracking-[0.08em] ${
                  state === "active"
                    ? "font-semibold text-ink"
                    : "text-muted"
                }`}
              >
                <span className="mr-1" aria-hidden>
                  {mark}
                </span>
                {STAGE_COPY[id]}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
