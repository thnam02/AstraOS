import type { ReactNode } from "react";

export function AstraMetric({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <p className="eyebrow">{label}</p>
      <p className="type-metric mt-1" title={hint}>
        {value}
      </p>
    </div>
  );
}

export function AstraMetricRow({
  items,
}: {
  items: { label: string; value: string | number; hint?: string }[];
}) {
  return (
    <dl
      className={`grid grid-cols-2 gap-px border border-line bg-line ${
        items.length === 3
          ? "sm:grid-cols-3"
          : items.length >= 5
            ? "sm:grid-cols-5"
            : "sm:grid-cols-4"
      }`}
    >
      {items.map((item) => (
        <div key={item.label} className="bg-canvas px-3 py-2">
          <dt className="text-[11px] text-muted">{item.label}</dt>
          <dd className="type-metric text-lg" title={item.hint}>
            {typeof item.value === "number"
              ? item.value.toLocaleString("en-AU")
              : item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
