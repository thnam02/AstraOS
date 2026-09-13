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

function stageLabelClass(state: RailState, preview: boolean): string {
  if (preview) return "font-medium text-muted";
  if (state === "active") return "font-semibold text-ink";
  if (state === "complete") return "font-medium text-ink";
  if (state === "failed" || state === "blocked") return "font-medium text-danger";
  return "font-medium text-muted";
}

export function StageNode({
  state,
  preview = false,
}: {
  state: RailState;
  preview?: boolean;
}) {
  if (preview) {
    return (
      <span
        aria-hidden
        className="relative z-10 flex h-3.5 w-3.5 shrink-0 rounded-full border border-line bg-canvas"
      />
    );
  }
  const mark =
    state === "complete"
      ? "✓"
      : state === "active"
        ? "●"
        : state === "failed" || state === "blocked"
          ? "!"
          : "";
  return (
    <span
      aria-hidden
      className={[
        "relative z-10 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border text-[8px] leading-none",
        "motion-safe:transition-colors",
        state === "complete" ? "border-mark bg-canvas text-mark" : "",
        state === "active" ? "border-mark bg-mark text-surface" : "",
        state === "failed" || state === "blocked"
          ? "border-danger bg-canvas text-danger"
          : "",
        state === "future" ? "border-line bg-canvas text-muted" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {mark}
    </span>
  );
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
        const isLast = index === LIVE_STAGES.length - 1;
        const connectorDone =
          !preview && (state === "complete" || state === "active");
        const body = (
          <span className="inline-flex items-center gap-1.5">
            <StageNode state={state} preview={preview} />
            <span className={`text-[13px] ${stageLabelClass(state, preview)}`}>
              {label}
            </span>
          </span>
        );

        return (
          <li key={id} className="relative flex items-center pr-5 last:pr-0">
            {!isLast ? (
              <span
                aria-hidden
                className={[
                  "pointer-events-none absolute top-1/2 left-[calc(100%-1.15rem)] h-px w-5 -translate-y-1/2",
                  connectorDone ? "bg-mark/45" : "bg-line",
                ].join(" ")}
              />
            ) : null}
            {interactive && onSelect && !preview ? (
              <button
                type="button"
                onClick={() => onSelect(id)}
                aria-current={state === "active" ? "step" : undefined}
                aria-label={spoken}
                className="cursor-pointer rounded-[4px] px-0.5 py-0.5 motion-safe:transition-colors hover:bg-surface-2/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
              >
                {body}
              </button>
            ) : (
              <span
                aria-current={!preview && state === "active" ? "step" : undefined}
                aria-label={spoken}
              >
                {body}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
