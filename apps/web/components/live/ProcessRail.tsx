import { cn } from "@/lib/utils";

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

/** Synchronous commerce rail — Learn is outcome follow-up, not a transaction step. */
export const COMMERCE_STAGES: LiveStage[] = [
  "understand",
  "qualify",
  "match",
  "construct",
  "optimise",
  "negotiate",
  "transact",
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
  size = "sm",
}: {
  state: RailState;
  preview?: boolean;
  size?: "sm" | "md";
}) {
  const dim = size === "md" ? "h-4 w-4 text-[9px]" : "h-3.5 w-3.5 text-[8px]";
  if (preview) {
    return (
      <span
        aria-hidden
        className={cn(
          "relative z-10 flex shrink-0 rounded-full border border-line bg-canvas",
          dim,
        )}
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
      className={cn(
        "relative z-10 flex shrink-0 items-center justify-center rounded-full border leading-none",
        dim,
        "motion-safe:transition-colors",
        state === "complete" && "border-mark bg-canvas text-mark",
        state === "active" && "border-mark bg-mark text-surface",
        (state === "failed" || state === "blocked") &&
          "border-danger bg-canvas text-danger",
        state === "future" && "border-line bg-canvas text-muted",
      )}
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
  spread = false,
}: {
  active: LiveStage;
  flags: Omit<Parameters<typeof processRailState>[1], never>;
  onSelect?: (stage: LiveStage) => void;
  interactive?: boolean;
  preview?: boolean;
  /** Span the workbench width with evenly spaced stages (LIVE entry). */
  spread?: boolean;
}) {
  const nodeSize = spread ? "md" : "sm";

  return (
    <ol
      className={cn(
        "flex items-center",
        spread ? "w-full min-w-[40rem]" : "min-w-max",
      )}
      aria-label={preview ? "How AstraOS works" : "Decision pipeline"}
    >
      {COMMERCE_STAGES.map((id, index) => {
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
        const isLast = index === COMMERCE_STAGES.length - 1;
        const connectorDone =
          !preview && (state === "complete" || state === "active");
        const body = (
          <span
            className={cn(
              "inline-flex items-center",
              spread ? "gap-2" : "gap-1.5",
            )}
          >
            <StageNode state={state} preview={preview} size={nodeSize} />
            <span
              className={cn(
                spread ? "text-[14px] md:text-[15px]" : "text-[13px]",
                stageLabelClass(state, preview),
              )}
            >
              {label}
            </span>
          </span>
        );

        return (
          <li
            key={id}
            className={cn(
              "relative flex items-center",
              spread
                ? "min-w-0 flex-1 justify-center pr-0"
                : "pr-5 last:pr-0",
            )}
          >
            {!isLast ? (
              <span
                aria-hidden
                className={cn(
                  "pointer-events-none absolute top-1/2 -translate-y-1/2",
                  spread
                    ? "left-[calc(50%+3.25rem)] right-[calc(-50%+3.25rem)] h-[2px]"
                    : "left-[calc(100%-1.15rem)] h-px w-5",
                  connectorDone ? "bg-mark/50" : "bg-line",
                )}
              />
            ) : null}
            {interactive && onSelect && !preview ? (
              <button
                type="button"
                onClick={() => onSelect(id)}
                aria-current={state === "active" ? "step" : undefined}
                aria-label={spoken}
                className={cn(
                  "cursor-pointer rounded-[var(--radius-control)] motion-safe:transition-colors hover:bg-surface-2/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                  spread ? "px-1.5 py-1.5" : "px-0.5 py-0.5",
                )}
              >
                {body}
              </button>
            ) : (
              <span
                aria-current={!preview && state === "active" ? "step" : undefined}
                aria-label={spoken}
                className={spread ? "px-1.5 py-1.5" : undefined}
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
