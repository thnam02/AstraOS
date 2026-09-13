import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function AstraPanel({
  children,
  className,
  raised = false,
  tone,
}: {
  children: ReactNode;
  className?: string;
  raised?: boolean;
  tone?: "primary" | "secondary";
}) {
  const resolved = tone ?? (raised ? "primary" : "secondary");
  return (
    <section
      className={cn(resolved === "primary" ? "stage-result" : "panel", className)}
    >
      {children}
    </section>
  );
}
