export function LiveStatus({
  label = "Live workbench",
  detail = "Merchant offer intelligence",
}: {
  label?: string;
  detail?: string;
}) {
  return (
    <div>
      <p className="inline-flex items-center gap-2">
        <span
          className="h-1.5 w-1.5 rounded-full bg-success"
          aria-hidden
        />
        <span className="eyebrow">{label}</span>
      </p>
      <p className="mt-1 type-small text-muted">{detail}</p>
    </div>
  );
}
