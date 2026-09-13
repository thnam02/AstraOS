import { AstraStatusBadge, type AstraTone } from "@/components/astra";
import type { ConnectionStatus } from "@/types";

const TONE: Record<ConnectionStatus, AstraTone> = {
  loading: "neutral",
  connected: "positive",
  unavailable: "negative",
};

const LABELS: Record<ConnectionStatus, string> = {
  loading: "Checking",
  connected: "Connected",
  unavailable: "Unavailable",
};

export function StatusBadge({ status }: { status: ConnectionStatus }) {
  return <AstraStatusBadge tone={TONE[status]}>{LABELS[status]}</AstraStatusBadge>;
}
