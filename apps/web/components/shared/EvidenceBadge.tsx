import { AstraSourceBadge } from "@/components/astra";
import type { SourceBadge } from "@/lib/matchDisplay";

export function EvidenceBadge({ source }: { source: SourceBadge }) {
  return <AstraSourceBadge code={source.code} title={source.title} />;
}
