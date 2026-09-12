import type { ConnectionStatus } from "@/types";

const STYLES: Record<ConnectionStatus, string> = {
  loading: "border-line bg-canvas text-muted",
  connected: "border-success/20 bg-success/5 text-success",
  unavailable: "border-danger/20 bg-danger/5 text-danger",
};

const DOT: Record<ConnectionStatus, string> = {
  loading: "bg-muted",
  connected: "bg-success",
  unavailable: "bg-danger",
};

const LABELS: Record<ConnectionStatus, string> = {
  loading: "Checking",
  connected: "Connected",
  unavailable: "Unavailable",
};

export function StatusBadge({ status }: { status: ConnectionStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-[6px] border px-2 py-1 text-xs font-medium ${STYLES[status]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${DOT[status]}`} />
      {LABELS[status]}
    </span>
  );
}
