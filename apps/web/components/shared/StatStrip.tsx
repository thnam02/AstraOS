import { AstraMetricRow } from "@/components/astra";

export function StatStrip({
  items,
}: {
  items: { label: string; value: string | number }[];
}) {
  return <AstraMetricRow items={items} />;
}
