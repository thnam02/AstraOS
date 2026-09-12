import type { ReactNode } from "react";

export function Disclosure({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <details className="border border-line">
      <summary className="cursor-pointer px-3 py-2 text-xs text-muted">
        {title}
      </summary>
      <div className="border-t border-line px-3 py-3">{children}</div>
    </details>
  );
}
