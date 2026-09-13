export function LiveStatus({
  label = "Live workbench"
}: {
  label?: string;
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
    </div>
  );
}
