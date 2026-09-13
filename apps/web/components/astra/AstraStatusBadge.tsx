import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type AstraTone = "positive" | "warning" | "negative" | "neutral" | "info";

const TONE: Record<AstraTone, string> = {
  positive: "border-success/20 bg-success/5 text-success",
  warning: "border-warning/20 bg-warning/5 text-warning",
  negative: "border-danger/20 bg-danger/5 text-danger",
  neutral: "border-line bg-canvas text-muted",
  info: "border-info/20 bg-info/5 text-info",
};

const LABEL: Record<AstraTone, string> = {
  positive: "Positive",
  warning: "Warning",
  negative: "Negative",
  neutral: "Neutral",
  info: "Information",
};

export function AstraStatusBadge({
  tone = "neutral",
  children,
}: {
  tone?: AstraTone;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-[var(--radius-control)] border px-1.5 py-0.5 text-[11px] font-medium",
        TONE[tone],
      )}
    >
      <span className="sr-only">{LABEL[tone]}: </span>
      {children}
    </span>
  );
}

export function AstraSourceBadge({
  code,
  title,
}: {
  code: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className="inline-flex items-center border border-line px-1 py-px text-[10px] tracking-[0.06em] text-muted"
    >
      {code}
    </span>
  );
}
