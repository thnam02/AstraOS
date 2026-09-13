export function AstraScore({
  value,
  label,
  display,
  suffix = "/ 100",
  size = "default",
}: {
  value: number;
  label?: string;
  display?: string;
  suffix?: string;
  size?: "default" | "large";
}) {
  const pct = Math.round(value * 100);
  const shown = display ?? String(pct);
  const numberClass =
    size === "large"
      ? "type-metric"
      : "font-mono text-sm font-medium tabular-nums";
  return (
    <div>
      {label ? (
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-xs text-muted">{label}</span>
          <span className={numberClass}>
            {shown}
            <span className="ml-1 text-xs font-normal text-muted">{suffix}</span>
          </span>
        </div>
      ) : (
        <p className={numberClass}>
          {shown}
          <span className="ml-1 text-xs font-normal text-muted">{suffix}</span>
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
        <div
          className="h-full bg-ink motion-safe:transition-[width] motion-safe:duration-300"
          style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
        />
      </div>
    </div>
  );
}
