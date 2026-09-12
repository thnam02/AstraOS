export function DataBadge({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "success" | "warning" | "danger";
  children: string;
}) {
  const styles = {
    neutral: "border-line bg-canvas text-muted",
    success: "border-success/20 bg-success/5 text-success",
    warning: "border-warning/20 bg-warning/5 text-warning",
    danger: "border-danger/20 bg-danger/5 text-danger",
  } as const;

  return (
    <span
      className={`inline-flex items-center rounded-[6px] border px-1.5 py-0.5 text-[11px] font-medium ${styles[tone]}`}
    >
      {children}
    </span>
  );
}
