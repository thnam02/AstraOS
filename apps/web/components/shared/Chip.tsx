import type { ReactNode } from "react";

export function Chip({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center border border-line bg-canvas px-2 py-0.5 text-xs">
      {children}
    </span>
  );
}
