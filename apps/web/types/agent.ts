export type AgentCapabilities = {
  service: string;
  protocol_name: string;
  version: string;
  operations: string[];
  supported: string[];
  not_supported: string[];
  protocol: string[];
  disclaimer: string;
};

export type AgentActivityItem = {
  occurred_at: string;
  kind: string;
  status: string;
  channel: "AGENT_API" | "OPERATOR" | "UNKNOWN";
  buyer_agent_id: string | null;
  request_id: string | null;
  negotiation_session_id: string;
  proposal_id: string | null;
  transaction_id: string | null;
  order_number: string | null;
  intent_summary: string;
  total_amount_cents: number | null;
  currency: string;
};

export type AgentActivityResponse = {
  items: AgentActivityItem[];
};

export type ReadyResponse = {
  status: string;
  service?: string;
  degraded_mode: string[];
  checks: { name: string; ok: boolean; detail: string; required?: boolean }[];
};
