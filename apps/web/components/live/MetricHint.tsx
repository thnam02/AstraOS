import { Info } from "@phosphor-icons/react";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function MetricHint({
  label,
  hint,
}: {
  label: string;
  hint: string;
}) {
  return (
    <span className="inline-flex items-center gap-1">
      {label}
      <Tooltip>
        <TooltipTrigger
          type="button"
          className="text-muted hover:text-ink"
          aria-label={`${label} definition`}
        >
          <Info size={12} aria-hidden />
        </TooltipTrigger>
        <TooltipContent className="max-w-xs border-line bg-surface text-ink shadow-none">
          {hint}
        </TooltipContent>
      </Tooltip>
    </span>
  );
}
