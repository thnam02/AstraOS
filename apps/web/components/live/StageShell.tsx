"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import { CaretLeft, CaretRight } from "@phosphor-icons/react";

import { STAGE_META, stageReachable } from "@/lib/liveStages";
import { cn } from "@/lib/utils";

import {
  LIVE_STAGES,
  processRailState,
  type LiveStage,
} from "./ProcessRail";

export function StageHeader({ stage }: { stage: LiveStage }) {
  const meta = STAGE_META[stage];
  return (
    <header className="max-w-3xl">
      <p className="eyebrow text-mark">
        {meta.number} · {meta.title}
      </p>
      <h2 className="mt-1.5 text-[1.65rem] font-semibold tracking-tight">
        {meta.heading}
      </h2>
      <p className="mt-1.5 max-w-2xl text-[15px] leading-6 text-muted">
        {meta.description}
      </p>
    </header>
  );
}

export function StageMetricStrip({
  items,
}: {
  items: { label: string; value: ReactNode; hint?: string }[];
}) {
  return (
    <dl className="grid gap-4 sm:grid-cols-3">
      {items.map((item) => (
        <div key={item.label}>
          <dt className="type-small text-muted">{item.label}</dt>
          <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
            {item.value}
          </dd>
          {item.hint ? (
            <p className="mt-0.5 text-xs text-muted">{item.hint}</p>
          ) : null}
        </div>
      ))}
    </dl>
  );
}

export function StageResult({
  label,
  title,
  value,
  explanation,
  metrics,
  actions,
  children,
  emphasis = false,
}: {
  label: string;
  title?: ReactNode;
  value?: ReactNode;
  explanation?: ReactNode;
  metrics?: { label: string; value: ReactNode; hint?: string }[];
  actions?: ReactNode;
  children?: ReactNode;
  emphasis?: boolean;
}) {
  return (
    <section className={cn("stage-result", emphasis && "stage-result-emphasis")}>
      <p className="eyebrow text-mark">{label}</p>
      {title || value ? (
        <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
          {title ? (
            <h3 className="text-[1.5rem] font-semibold tracking-tight">{title}</h3>
          ) : null}
          {value ? (
            <p className="font-mono text-2xl font-semibold tabular-nums">{value}</p>
          ) : null}
        </div>
      ) : null}
      {explanation ? (
        <div className="mt-3 max-w-2xl text-[15px] leading-6">{explanation}</div>
      ) : null}
      {metrics?.length ? (
        <div className="mt-6 border-t border-line-muted pt-5">
          <StageMetricStrip items={metrics} />
        </div>
      ) : null}
      {children ? <div className="mt-5">{children}</div> : null}
      {actions ? (
        <div className="mt-6 flex flex-wrap items-center gap-3">{actions}</div>
      ) : null}
    </section>
  );
}

export function StageSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section>
      <p className="eyebrow">{title}</p>
      {description ? (
        <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>
      ) : null}
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function StageDisclosure({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        className="btn-quiet"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {title}
      </button>
      {open ? <div className="mt-3">{children}</div> : null}
    </div>
  );
}

export function StagePrimaryAction({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
}) {
  if (!onClick) return null;
  return (
    <button
      type="button"
      className="btn-primary"
      disabled={disabled}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

export function StageLayout({
  children,
  wide = false,
}: {
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className={cn("space-y-8", wide ? "max-w-[1280px]" : "max-w-[1120px]")}>
      {children}
    </div>
  );
}

export function StageFooter({
  stage,
  flags,
  onSelect,
}: {
  stage: LiveStage;
  flags: Parameters<typeof processRailState>[1];
  onSelect: (next: LiveStage) => void;
}) {
  const index = LIVE_STAGES.indexOf(stage);
  const previous = index > 0 ? LIVE_STAGES[index - 1] : null;
  const next = index < LIVE_STAGES.length - 1 ? LIVE_STAGES[index + 1] : null;
  const previousEnabled = previous && stageReachable(previous, flags, stage);
  const nextEnabled = next && stageReachable(next, flags, stage);

  return (
    <nav
      className="flex max-w-[1120px] flex-wrap items-start justify-between gap-4 border-t border-line pt-6"
      aria-label="Stage"
    >
      {previous && previousEnabled ? (
        <button
          type="button"
          className="btn-quiet text-left"
          onClick={() => onSelect(previous)}
        >
          <span className="flex items-center gap-1 text-xs text-muted">
            <CaretLeft size={12} aria-hidden />
            {STAGE_META[previous].number} {STAGE_META[previous].title}
          </span>
          <span className="mt-1 block text-sm font-medium">
            {STAGE_META[previous].subtitle}
          </span>
        </button>
      ) : (
        <span />
      )}
      {next && nextEnabled ? (
        <button
          type="button"
          className="btn-quiet ml-auto text-right"
          onClick={() => onSelect(next)}
        >
          <span className="flex items-center justify-end gap-1 text-xs text-muted">
            {STAGE_META[next].number} {STAGE_META[next].title}
            <CaretRight size={12} aria-hidden />
          </span>
          <span className="mt-1 block text-sm font-medium">
            {STAGE_META[next].subtitle}
          </span>
        </button>
      ) : (
        <span />
      )}
    </nav>
  );
}
