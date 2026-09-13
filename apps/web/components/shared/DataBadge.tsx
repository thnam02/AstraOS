import { AstraStatusBadge, type AstraTone } from "@/components/astra";

const TONE: Record<string, AstraTone> = {
  neutral: "neutral",
  success: "positive",
  warning: "warning",
  danger: "negative",
  uncertain: "info",
};

export function DataBadge({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "success" | "warning" | "danger" | "uncertain";
  children: string;
}) {
  return <AstraStatusBadge tone={TONE[tone]}>{children}</AstraStatusBadge>;
}
