export function StatStrip({
  items,
}: {
  items: { label: string; value: string | number }[];
}) {
  return (
    <dl
      className={`grid grid-cols-2 gap-px border border-line bg-line ${
        items.length === 3
          ? "sm:grid-cols-3"
          : items.length === 5
            ? "sm:grid-cols-5"
            : "sm:grid-cols-4"
      }`}
    >
      {items.map((item) => (
        <div key={item.label} className="bg-canvas px-3 py-2">
          <dt className="text-[11px] text-muted">{item.label}</dt>
          <dd className="font-mono text-lg font-semibold tabular-nums">
            {typeof item.value === "number"
              ? item.value.toLocaleString()
              : item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
