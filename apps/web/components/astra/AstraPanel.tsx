import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function AstraPanel({
  children,
  className,
  raised = false,
}: {
  children: ReactNode;
  className?: string;
  raised?: boolean;
}) {
  return (
    <section className={cn(raised ? "panel-decision" : "panel", className)}>
      {children}
    </section>
  );
}
