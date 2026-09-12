export function ScoreBar({
  value,
  label,
  large = false,
  display,
  suffix,
}: {
  value: number;
  label?: string;
  large?: boolean;
  display?: string;
  suffix?: string;
}) {
  const pct = Math.round(value * 100);
  const shown = display ?? String(pct);
  return (
    <div>
      {label ? (
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-xs text-muted" title="How strongly the product itself aligns with buyer context and preferences.">
            {label}
          </span>
          <span
            className={`font-mono tabular-nums ${
              large ? "text-4xl font-semibold" : "text-sm font-medium"
            }`}
          >
            {shown}
            {suffix ? (
              <span className="ml-1 text-xs font-normal text-muted">{suffix}</span>
            ) : null}
          </span>
        </div>
      ) : (
        <p
          className={`font-mono tabular-nums ${
            large ? "text-4xl font-semibold" : "text-sm font-medium"
          }`}
        >
          {shown}
          {suffix ? (
            <span className="ml-1 text-xs font-normal text-muted">{suffix}</span>
          ) : null}
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
