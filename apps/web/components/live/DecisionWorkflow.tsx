"use client";

import { useEffect, useRef, useState } from "react";
import { CaretLeft, CaretRight } from "@phosphor-icons/react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { STAGE_META, stageReachable } from "@/lib/liveStages";
import { cn } from "@/lib/utils";

import {
  LIVE_STAGES,
  processRailState,
  StageNode,
  type LiveStage,
  type RailState,
} from "./ProcessRail";

type Flags = Parameters<typeof processRailState>[1];

function spokenState(state: RailState): string {
  if (state === "complete") return "complete";
  if (state === "active") return "active";
  if (state === "failed" || state === "blocked") return "error";
  return "pending";
}

function neighbor(
  active: LiveStage,
  flags: Flags,
  offset: -1 | 1,
): LiveStage | null {
  const index = LIVE_STAGES.indexOf(active) + offset;
  const id = LIVE_STAGES[index] ?? null;
  if (!id || !stageReachable(id, flags, active)) return null;
  return id;
}

function FullWorkflow({
  active,
  flags,
  onSelect,
}: {
  active: LiveStage;
  flags: Flags;
  onSelect: (stage: LiveStage) => void;
}) {
  return (
    <nav className="overflow-x-auto" aria-label="Decision workflow">
      <ol className="flex min-h-[56px] min-w-max items-stretch">
        {LIVE_STAGES.map((id, index) => {
          const meta = STAGE_META[id];
          const state = processRailState(id, flags, active);
          const disabled = !stageReachable(id, flags, active);
          const connectorDone = state === "complete" || state === "active";
          const isLast = index === LIVE_STAGES.length - 1;

          return (
            <li
              key={id}
              className="relative flex min-w-[5.75rem] flex-1 basis-0 justify-center"
            >
              {!isLast ? (
                <span
                  aria-hidden
                  className={cn(
                    "pointer-events-none absolute top-[13px] left-[calc(50%+0.55rem)] right-[-50%] h-px",
                    connectorDone ? "bg-mark/45" : "bg-line",
                  )}
                />
              ) : null}
              <button
                type="button"
                disabled={disabled}
                onClick={() => onSelect(id)}
                aria-current={state === "active" ? "step" : undefined}
                aria-label={`${meta.number} ${meta.title}, ${spokenState(state)}`}
                className={cn(
                  "group relative flex w-full max-w-[7rem] flex-col items-center px-1 py-1 text-center",
                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                  "motion-safe:transition-colors",
                  disabled
                    ? "cursor-not-allowed opacity-55"
                    : "cursor-pointer hover:bg-surface-2/80",
                  state === "active" &&
                    "border-b-2 border-mark pb-[calc(0.25rem-2px)]",
                )}
              >
                <StageNode state={state} />
                <span
                  className={cn(
                    "mt-0.5 text-[9px] font-medium leading-none tracking-[0.08em]",
                    state === "active"
                      ? "text-mark"
                      : state === "failed" || state === "blocked"
                        ? "text-danger"
                        : "text-muted",
                  )}
                >
                  {meta.number}
                </span>
                <span
                  className={cn(
                    "mt-0.5 text-[12px] leading-none",
                    state === "active" && "font-semibold text-ink",
                    state === "complete" && "font-medium text-ink",
                    (state === "failed" || state === "blocked") &&
                      "font-medium text-danger",
                    state === "future" && "font-medium text-muted",
                  )}
                >
                  {meta.title}
                </span>
                <span className="mt-0.5 text-[10px] leading-none text-muted">
                  {meta.subtitle}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function WorkflowPicker({
  active,
  flags,
  onSelect,
}: {
  active: LiveStage;
  flags: Flags;
  onSelect: (stage: LiveStage) => void;
}) {
  const current = STAGE_META[active];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="inline-flex min-w-0 items-center justify-center gap-2 px-2 text-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
        aria-label={`${current.number} ${current.title}, open workflow`}
      >
        <span className="truncate text-[13px] font-semibold tracking-tight">
          <span className="sm:hidden">
            {current.number} / 08 · {current.title.toUpperCase()}
          </span>
          <span className="hidden sm:inline">
            {current.number} · {current.title.toUpperCase()}
            <span className="font-medium text-muted">
              {" "}
              / {current.subtitle}
            </span>
          </span>
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="center"
        className="w-56 rounded-[var(--radius-control)] border-line p-1 shadow-none"
      >
        {LIVE_STAGES.map((id) => {
          const meta = STAGE_META[id];
          const state = processRailState(id, flags, active);
          const disabled = !stageReachable(id, flags, active);
          return (
            <DropdownMenuItem
              key={id}
              disabled={disabled}
              aria-current={state === "active" ? "step" : undefined}
              onSelect={() => onSelect(id)}
              className={cn(
                "cursor-pointer rounded-[4px] text-[13px]",
                state === "active" && "bg-canvas font-medium",
                disabled && "cursor-not-allowed",
              )}
            >
              <span className="w-8 text-[11px] text-muted">{meta.number}</span>
              <span>{meta.title}</span>
              <span className="ml-auto text-[11px] text-muted">
                {state === "complete" ? "✓" : meta.subtitle}
              </span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function CompactWorkflow({
  visible,
  active,
  flags,
  onSelect,
}: {
  visible: boolean;
  active: LiveStage;
  flags: Flags;
  onSelect: (stage: LiveStage) => void;
}) {
  const previous = neighbor(active, flags, -1);
  const next = neighbor(active, flags, 1);

  return (
    <div
      className={cn(
        "fixed inset-x-0 top-12 z-20 border-b border-line bg-surface transition duration-150 ease-out",
        visible
          ? "translate-y-0 opacity-100"
          : "pointer-events-none -translate-y-1 opacity-0",
      )}
      aria-hidden={!visible}
      inert={!visible || undefined}
    >
      <nav
        className="page-shell flex h-12 items-center justify-between gap-3"
        aria-label="Compact decision workflow"
      >
        <button
          type="button"
          disabled={!previous}
          onClick={() => previous && onSelect(previous)}
          className="btn-quiet inline-flex min-w-0 items-center gap-1 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <CaretLeft size={14} aria-hidden />
          <span className="hidden truncate sm:inline">
            {previous
              ? `${STAGE_META[previous].number} ${STAGE_META[previous].title}`
              : "Previous"}
          </span>
        </button>
        <WorkflowPicker active={active} flags={flags} onSelect={onSelect} />
        <button
          type="button"
          disabled={!next}
          onClick={() => next && onSelect(next)}
          className="btn-quiet inline-flex min-w-0 items-center gap-1 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <span className="hidden truncate sm:inline">
            {next ? STAGE_META[next].title : "Next"}
          </span>
          <CaretRight size={14} aria-hidden />
        </button>
      </nav>
    </div>
  );
}

export function DecisionWorkflow({
  active,
  flags,
  onSelect,
}: {
  active: LiveStage;
  flags: Flags;
  onSelect: (stage: LiveStage) => void;
}) {
  const fullRef = useRef<HTMLDivElement>(null);
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    const node = fullRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        setCompact(!entry.isIntersecting);
      },
      { rootMargin: "-48px 0px 0px 0px", threshold: 0 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <div
        ref={fullRef}
        className="-mx-6 border-b border-line-muted px-6 py-1"
      >
        <FullWorkflow active={active} flags={flags} onSelect={onSelect} />
      </div>
      <CompactWorkflow
        visible={compact}
        active={active}
        flags={flags}
        onSelect={onSelect}
      />
    </>
  );
}
