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
): RailState {
  if (flags.txnFailed && id === "transact") return "failed";
  if (!flags.hasMatch) {
    return id === "understand" ? "active" : "future";
  }
  if (id === "understand" || id === "qualify" || id === "match") return "complete";
  if (id === "construct") return flags.hasOffers ? "complete" : "future";
  if (id === "optimise") return flags.hasOpt ? "complete" : "future";
  if (id === "negotiate") return flags.hasNego ? "complete" : "future";
  if (id === "transact") {
    if (flags.txnComplete) return "complete";
    if (flags.hasTxn) return "active";
    return flags.hasNego ? "future" : "future";
  }
  return flags.txnComplete ? "complete" : "future";
}

export function ProcessRail({
  active,
  flags,
  onSelect,
}: {
  active: LiveStage;
  flags: Parameters<typeof processRailState>[1];
  onSelect: (stage: LiveStage) => void;
}) {
  return (
    <ol className="flex flex-wrap gap-1" aria-label="Decision pipeline">
      {LIVE_STAGES.map((id) => {
        const state = processRailState(id, flags);
        const selected = active === id;
        return (
          <li key={id}>
            <button
              type="button"
              onClick={() => onSelect(id)}
              className={`px-2 py-1 text-[11px] uppercase tracking-[0.06em] ${
                selected
                  ? "bg-ink text-surface"
                  : state === "complete"
                    ? "border border-ink/20 bg-canvas text-ink"
                    : state === "failed"
                      ? "border border-danger/40 text-danger"
                      : "border border-line text-muted"
              }`}
            >
              {id}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
