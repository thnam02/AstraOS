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
        <span className="text-[11px] font-medium tracking-[0.08em] text-muted uppercase md:text-xs md:tracking-[0.07em]">
          {label}
        </span>
      </p>
    </div>
  );
}
