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

export const STAGE_COPY: Record<LiveStage, string> = {
  understand: "Understand",
  qualify: "Qualify",
  match: "Match",
  construct: "Construct",
  optimise: "Optimise",
  negotiate: "Negotiate",
  transact: "Transact",
  learn: "Learn",
};

function stageClass(state: RailState, preview: boolean): string {
  if (preview) return "font-medium text-muted";
  if (state === "active") return "font-semibold text-ink";
  if (state === "complete") return "font-medium text-ink";
  if (state === "failed" || state === "blocked") return "font-medium text-danger";
  return "font-medium text-muted";
}

export function ProcessRail({
  active,
  flags,
  onSelect,
  interactive = true,
  preview = false,
}: {
  active: LiveStage;
  flags: Omit<Parameters<typeof processRailState>[1], never>;
  onSelect?: (stage: LiveStage) => void;
  interactive?: boolean;
  preview?: boolean;
}) {
  return (
    <ol
      className="flex min-w-max items-center"
      aria-label={preview ? "How AstraOS works" : "Decision pipeline"}
    >
      {LIVE_STAGES.map((id, index) => {
        const state = preview ? "future" : processRailState(id, flags, active);
        const mark =
          state === "complete"
            ? "✓"
            : state === "active"
              ? "●"
              : state === "failed" || state === "blocked"
                ? "!"
                : "○";
        const label = STAGE_COPY[id];
        const spoken = preview
          ? label
          : `${label}, ${
              state === "complete"
                ? "complete"
                : state === "active"
                  ? "active"
                  : state === "failed" || state === "blocked"
                    ? "error"
                    : "pending"
            }`;
        return (
          <li key={id} className="flex items-center">
            {index > 0 ? (
              <span className="mx-2 h-px w-5 shrink-0 bg-line" aria-hidden />
            ) : null}
            {interactive && onSelect && !preview ? (
              <button
                type="button"
                onClick={() => onSelect(id)}
                aria-current={state === "active" ? "step" : undefined}
                aria-label={spoken}
                className={`cursor-pointer text-[13px] motion-safe:transition-colors ${stageClass(state, preview)}`}
              >
                <span className="mr-1.5" aria-hidden>
                  {mark}
                </span>
                {label}
              </button>
            ) : (
              <span
                aria-current={!preview && state === "active" ? "step" : undefined}
                aria-label={spoken}
                className={`text-[13px] ${stageClass(state, preview)}`}
              >
                {preview ? null : (
                  <span className="mr-1.5" aria-hidden>
                    {mark}
                  </span>
                )}
                {label}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
