"use client";

import { STAGE_META, stageReachable } from "@/lib/liveStages";
import { cn } from "@/lib/utils";

import { LIVE_STAGES, processRailState, type LiveStage } from "./ProcessRail";

type Flags = Parameters<typeof processRailState>[1];

export function DecisionWorkflow({
  active,
  flags,
  onSelect,
  preview = false,
}: {
  active: LiveStage;
  flags: Flags;
  onSelect?: (stage: LiveStage) => void;
  preview?: boolean;
}) {
  return (
    <footer className="sticky bottom-0 z-20 -mx-6 mt-auto border-t border-line bg-surface px-6 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-widest text-ink">
          Decision pipeline
        </p>
        <p className="text-xs text-muted">
          {preview
            ? "From buyer intent to order and outcome"
            : "Explore the decision trace"}
        </p>
      </div>
      <nav className="overflow-x-auto" aria-label="Decision workflow">
        <ol className="grid min-w-[880px] grid-cols-8 gap-2">
          {LIVE_STAGES.map((id) => {
            const meta = STAGE_META[id];
            const state = preview
              ? "future"
              : processRailState(id, flags, active);
            const disabled = !stageReachable(id, flags, active);
            const status = state === "future" ? "pending" : state;
            const body = (
              <>
                <span className="flex items-center justify-between gap-2">
                  <span className="font-mono text-sm tabular-nums">
                    {meta.number}
                  </span>
                  {!preview && (
                    <span className="text-[10px] uppercase tracking-wide">
                      {state === "complete" ? "✓ Done" : status}
                    </span>
                  )}
                </span>
                <span className="mt-2 block text-base font-semibold">
                  {meta.title}
                </span>
                <span className="mt-1 block text-xs text-muted">
                  {meta.subtitle}
                </span>
              </>
            );
            const style = cn(
              "block w-full border-t-2 px-3 py-2 text-left",
              state === "active"
                ? "border-mark bg-canvas text-mark"
                : "border-line text-ink",
              state === "complete" && "border-mark",
              (state === "failed" || state === "blocked") &&
                "border-danger text-danger",
            );
            return (
              <li key={id}>
                {preview ? (
                  <div className={style}>{body}</div>
                ) : (
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => onSelect?.(id)}
                    aria-current={state === "active" ? "step" : undefined}
                    aria-label={`${meta.number} ${meta.title}, ${status}`}
                    className={cn(
                      style,
                      "motion-safe:transition-colors disabled:cursor-not-allowed disabled:opacity-50 enabled:cursor-pointer enabled:hover:bg-canvas",
                    )}
                  >
                    {body}
                  </button>
                )}
              </li>
            );
          })}
        </ol>
      </nav>
    </footer>
  );
}
