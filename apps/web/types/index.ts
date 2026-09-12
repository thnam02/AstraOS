export type HealthResponse = {
  status: string;
  service: string;
};

export type ConnectionStatus = "loading" | "connected" | "unavailable";
