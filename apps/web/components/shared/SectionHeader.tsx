export function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
}) {
  return (
    <header className="space-y-2">
      {eyebrow ? (
        <p className="text-xs font-medium tracking-[0.14em] text-muted uppercase">
          {eyebrow}
        </p>
      ) : null}
      <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
      {description ? (
        <p className="max-w-xl text-sm leading-6 text-muted">{description}</p>
      ) : null}
    </header>
  );
}
