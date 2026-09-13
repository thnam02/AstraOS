import type { ReactNode } from "react";

export function AstraSectionHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 space-y-1">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1 className="type-page text-ink">{title}</h1>
        {description ? (
          <p className="max-w-2xl type-body text-muted">{description}</p>
        ) : null}
      </div>
      {action}
    </header>
  );
}

export function AstraStageHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <header className="space-y-1">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="type-section">{title}</h2>
      {description ? <p className="type-small text-muted">{description}</p> : null}
    </header>
  );
}
