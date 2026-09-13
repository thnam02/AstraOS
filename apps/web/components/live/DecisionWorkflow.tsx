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
      <p className="eyebrow mb-2">Decision workflow</p>
      <ol className="flex min-w-max items-stretch">
        {LIVE_STAGES.map((id) => {
          const meta = STAGE_META[id];
          const state = processRailState(id, flags, active);
          const disabled = !stageReachable(id, flags, active);
          return (
            <li key={id} className="min-w-[6.5rem] flex-1">
              <button
                type="button"
                disabled={disabled}
                onClick={() => onSelect(id)}
                aria-current={state === "active" ? "step" : undefined}
                aria-label={`${meta.number} ${meta.title}, ${spokenState(state)}`}
                className={cn(
                  "flex h-full w-full flex-col items-start border-l px-2.5 py-1.5 text-left",
                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                  disabled
                    ? "cursor-not-allowed border-line text-muted"
                    : "cursor-pointer border-line hover:bg-surface",
                  state === "active" && "border-l-mark bg-surface text-ink",
                  state === "complete" && "border-l-line",
                  state === "failed" && "border-l-danger",
                )}
              >
                <span
                  className={cn(
                    "flex items-center gap-1.5 text-[11px] tracking-[0.08em]",
                    state === "active" ? "text-mark" : "text-muted",
                  )}
                >
                  {state === "complete" ? (
                    <span aria-hidden className="text-mark">
                      ✓
                    </span>
                  ) : state === "active" ? (
                    <span aria-hidden>●</span>
                  ) : state === "failed" ? (
                    <span aria-hidden className="text-danger">
                      !
                    </span>
                  ) : (
                    <span aria-hidden>○</span>
                  )}
                  {meta.number}
                </span>
                <span
                  className={cn(
                    "mt-0.5 text-[13px] font-semibold",
                    disabled ? "text-muted" : "text-ink",
                  )}
                >
                  {meta.title}
                </span>
                <span className="text-[11px] text-muted">{meta.subtitle}</span>
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
        className="w-56 rounded-[6px] border-line p-1 shadow-none"
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
        "fixed inset-x-0 top-14 z-20 border-b border-line bg-surface transition duration-150 ease-out",
        visible
          ? "translate-y-0 opacity-100"
          : "pointer-events-none -translate-y-1 opacity-0",
      )}
      aria-hidden={!visible}
      inert={!visible || undefined}
    >
      <nav
        className="mx-auto flex h-12 w-full max-w-[1480px] items-center justify-between gap-3 px-6"
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
      { rootMargin: "-56px 0px 0px 0px", threshold: 0 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <div
        ref={fullRef}
        className="-mx-6 border-b border-line bg-surface px-6 py-3"
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
