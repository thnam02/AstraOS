"use client";

import { useId, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function SectionTabs({
  label,
  items,
  equalHeight = false,
}: {
  label: string;
  equalHeight?: boolean;
  items: { label: string; content: ReactNode }[];
}) {
  const [selected, setSelected] = useState(0);
  const id = useId();
  const current = Math.min(selected, items.length - 1);
  return (
    <div className="min-w-0 space-y-3">
      <div
        className="flex flex-wrap gap-1 border-b border-line pb-2"
        role="group"
        aria-label={label}
      >
        {items.map((item, index) => (
          <button
            key={item.label}
            type="button"
            aria-pressed={index === current}
            aria-controls={`${id}-panel-${index}`}
            onClick={() => setSelected(index)}
            className={cn(
              "rounded-[var(--radius-control)] px-3 py-2 text-sm font-medium",
              index === current
                ? "bg-ink text-surface"
                : "cursor-pointer text-muted hover:bg-surface",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className={equalHeight ? "grid" : undefined}>
        {items.map((item, index) => (
          <div
            key={item.label}
            id={`${id}-panel-${index}`}
            role="region"
            aria-label={item.label}
            hidden={!equalHeight && index !== current}
            aria-hidden={index !== current || undefined}
            inert={index !== current || undefined}
            className={cn(
              equalHeight && "col-start-1 row-start-1 min-w-0 [&>*]:h-full",
              equalHeight &&
                index !== current &&
                "invisible pointer-events-none",
            )}
          >
            {item.content}
          </div>
        ))}
      </div>
    </div>
  );
}
