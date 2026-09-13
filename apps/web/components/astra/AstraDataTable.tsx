import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function AstraDataTable({
  children,
  className,
  bordered = true,
}: {
  children: ReactNode;
  className?: string;
  bordered?: boolean;
}) {
  return (
    <div className={cn("overflow-x-auto", bordered && "border border-line")}>
      <table className={cn("table-dense w-full text-left text-sm", className)}>
        {children}
      </table>
    </div>
  );
}
