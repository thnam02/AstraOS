import type { ReactNode } from "react";

import { AstraPanel } from "@/components/astra";

export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <AstraPanel className={className}>{children}</AstraPanel>;
}
