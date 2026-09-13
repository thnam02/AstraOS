import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function AstraDataTable({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className="overflow-x-auto border border-line">
      <table className={cn("table-dense w-full text-left text-sm", className)}>
        {children}
      </table>
    </div>
  );
}
