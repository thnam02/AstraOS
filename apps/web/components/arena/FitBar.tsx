import { formatUtilityShort } from "@/lib/format";

export function FitBar({
  value,
  compact = false,
}: {
  value: number;
  compact?: boolean;
}) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="eyebrow" title="Transparent simulated buyer utility">
          Buyer Utility
        </span>
        <span
          className={`font-mono tabular-nums ${
            compact ? "text-lg font-semibold" : "text-2xl font-semibold"
          }`}
        >
          {formatUtilityShort(value)}
        </span>
      </div>
      <div
        className="mt-1 h-1.5 w-full bg-line"
        role="meter"
        aria-label="Transparent simulated buyer utility"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="h-full bg-ink" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
