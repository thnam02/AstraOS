import type { SourceBadge } from "@/lib/matchDisplay";

export function EvidenceBadge({ source }: { source: SourceBadge }) {
  return (
    <span
      title={source.title}
      className="inline-flex items-center border border-line px-1 py-px text-[10px] tracking-[0.06em] text-muted"
    >
      {source.code}
    </span>
  );
}
