export function ScoreBar({
  value,
  label,
  large = false,
}: {
  value: number;
  label?: string;
  large?: boolean;
}) {
  const pct = Math.round(value * 100);
  return (
    <div>
      {label ? (
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-xs text-muted">{label}</span>
          <span
            className={`font-mono tabular-nums ${
              large ? "text-3xl font-semibold" : "text-sm font-medium"
            }`}
          >
            {pct}
          </span>
        </div>
      ) : (
        <p
          className={`font-mono tabular-nums ${
            large ? "text-3xl font-semibold" : "text-sm font-medium"
          }`}
        >
          {pct}
        </p>
      )}
      <div
        className="mt-1 h-1.5 w-full bg-line"
        role="meter"
        aria-label={label ?? "Score"}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="h-full bg-ink" style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
      </div>
    </div>
  );
}
