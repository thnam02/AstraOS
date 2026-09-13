import type { ReactNode } from "react";

export function AstraEmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="border border-dashed border-line px-4 py-6">
      <p className="type-card">{title}</p>
      <p className="mt-1 type-body text-muted">{body}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

export function AstraErrorState({
  title = "Something went wrong",
  message,
  next,
}: {
  title?: string;
  message: string;
  next?: string;
}) {
  return (
    <div
      role="alert"
      className="border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger"
    >
      <p className="font-medium">{title}</p>
      <p className="mt-1">{message}</p>
      {next ? <p className="mt-1 text-muted">{next}</p> : null}
    </div>
  );
}

export function AstraLoadingState({
  title,
  steps,
}: {
  title: string;
  steps: readonly string[];
}) {
  return (
    <div className="mx-auto max-w-lg py-14" role="status" aria-live="polite">
      <p className="eyebrow">AstraOS Live</p>
      <h1 className="type-page mt-2">{title}</h1>
      <ol className="mt-6 space-y-2 text-sm">
        {steps.map((line, index) => (
          <li
            key={line}
            className={index === 0 ? "text-ink" : "text-muted"}
          >
            <span aria-hidden>{index === 0 ? "●" : "○"} </span>
            {line}
          </li>
        ))}
      </ol>
    </div>
  );
}
