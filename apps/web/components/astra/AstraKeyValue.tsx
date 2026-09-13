import type { ReactNode } from "react";

export function AstraKeyValue({
  rows,
}: {
  rows: { label: string; value: ReactNode }[];
}) {
  return (
    <dl className="space-y-1.5 text-sm">
      {rows.map((row) => (
        <div key={row.label} className="flex justify-between gap-4">
          <dt className="text-muted">{row.label}</dt>
          <dd className="text-right font-medium">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function AstraDelta({
  label,
  from,
  to,
  delta,
}: {
  label: string;
  from: string;
  to: string;
  delta?: string;
}) {
  return (
    <p className="text-sm">
      <span className="text-muted">{label} </span>
      {from} → {to}
      {delta ? <span className="text-muted"> ({delta})</span> : null}
    </p>
  );
}

export function AstraCallout({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <aside className="border border-line-muted bg-surface-2 px-3 py-2">
      <p className="eyebrow">{title}</p>
      <div className="mt-1 type-small text-muted">{children}</div>
    </aside>
  );
}

export function AstraTimeline({
  steps,
}: {
  steps: { label: string; state: "complete" | "active" | "future" | "failed" }[];
}) {
  return (
    <ol className="space-y-1 text-sm" aria-label="Progress">
      {steps.map((step) => {
        const mark =
          step.state === "complete"
            ? "✓"
            : step.state === "active"
              ? "●"
              : step.state === "failed"
                ? "!"
                : "○";
        return (
          <li
            key={step.label}
            className={
              step.state === "failed"
                ? "text-danger"
                : step.state === "future"
                  ? "text-muted"
                  : "text-ink"
            }
          >
            <span aria-hidden>{mark} </span>
            {step.label}
          </li>
        );
      })}
    </ol>
  );
}
