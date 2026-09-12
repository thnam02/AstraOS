import type { ReactNode } from "react";

export function StatTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  const display =
    typeof value === "number" ? value.toLocaleString() : value;

  return (
    <div className="min-w-0 border border-line bg-canvas px-3 py-3">
      <p className="text-[11px] leading-4 text-muted">{label}</p>
      <p className="mt-1 font-mono text-lg font-semibold tabular-nums tracking-tight text-ink">
        {display}
      </p>
      {hint ? <p className="mt-1 text-xs leading-4 text-muted">{hint}</p> : null}
    </div>
  );
}

export function StatRow({
  children,
  columns = 4,
}: {
  children: ReactNode;
  columns?: 3 | 4 | 5 | 7;
}) {
  const cols =
    columns === 3
      ? "sm:grid-cols-3"
      : columns === 5
        ? "sm:grid-cols-3 xl:grid-cols-5"
        : columns === 7
          ? "sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7"
          : "sm:grid-cols-2 lg:grid-cols-4";

  return <div className={`grid grid-cols-2 gap-2 ${cols}`}>{children}</div>;
}
