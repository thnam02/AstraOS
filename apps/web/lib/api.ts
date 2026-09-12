import { API_BASE_URL } from "@/lib/config";
import type {
  CatalogueStatsResponse,
  IngestionResultResponse,
  IngestionRunSummary,
  MerchantDataStatusResponse,
  HealthResponse,
  MerchantObjectiveResponse,
  MerchantObjectiveUpdate,
  MerchantPolicyResponse,
  MerchantPolicyUpdate,
  ProductDetail,
  ProductListResponse,
  ProductVariantDetail,
  QualifyResponse,
  QualificationVariantDetail,
  MatchResponse,
  GenerateOffersResponse,
  OfferDetailResponse,
  OfferRunResponse,
  BuyerProfile,
  DecisionResponse,
  OptimisationResponse,
  NegotiationResponse,
  AcceptProposalResponse,
  DemoStateResponse,
  ArenaRunResponse,
  ArenaBenchmarkCreated,
  ArenaBenchmarkResponse,
  LearningOverview,
  LearningDatasetSummary,
  LearningTrainResponse,
} from "@/types";

export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(`Request failed: ${response.status}`, response.status);
  }

  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getReady(): Promise<{
  status: string;
  degraded_mode: string[];
  checks: { name: string; ok: boolean; detail: string }[];
}> {
  return request("/ready");
}

export function getCatalogueStats(): Promise<CatalogueStatsResponse> {
  return request<CatalogueStatsResponse>("/api/v1/catalogue/stats");
}

export function getMerchantDataStatus(): Promise<MerchantDataStatusResponse> {
  return request<MerchantDataStatusResponse>("/api/v1/merchant/ingestion/status");
}

export function validateMerchantFeed(payload: {
  source_type: "json" | "csv";
  source_name: string;
  snapshot?: Record<string, unknown>;
  content_base64?: string;
}): Promise<IngestionResultResponse> {
  return request<IngestionResultResponse>("/api/v1/merchant/ingestion/validate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function importMerchantFeed(payload: {
  source_type: "json" | "csv";
  source_name: string;
  snapshot?: Record<string, unknown>;
  content_base64?: string;
}): Promise<IngestionResultResponse> {
  return request<IngestionResultResponse>("/api/v1/merchant/ingestion/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listIngestionRuns(): Promise<{ items: IngestionRunSummary[] }> {
  return request<{ items: IngestionRunSummary[] }>(
    "/api/v1/merchant/ingestion/runs",
  );
}

export function listProducts(params?: {
  brand?: string;
  category?: string;
  activeOnly?: boolean;
  limit?: number;
  offset?: number;
}): Promise<ProductListResponse> {
  const search = new URLSearchParams();
  if (params?.brand) search.set("brand", params.brand);
  if (params?.category) search.set("category", params.category);
  if (params?.activeOnly !== undefined) {
    search.set("active_only", String(params.activeOnly));
  }
  search.set("limit", String(params?.limit ?? 200));
  search.set("offset", String(params?.offset ?? 0));
  return request<ProductListResponse>(`/api/v1/catalogue/products?${search}`);
}

export function getProduct(productId: string): Promise<ProductDetail> {
  return request<ProductDetail>(`/api/v1/catalogue/products/${productId}`);
}

export function getVariant(variantId: string): Promise<ProductVariantDetail> {
  return request<ProductVariantDetail>(`/api/v1/catalogue/variants/${variantId}`);
}

export function getMerchantPolicy(): Promise<MerchantPolicyResponse> {
  return request<MerchantPolicyResponse>("/api/v1/merchant/policy");
}

export function updateMerchantPolicy(
  payload: MerchantPolicyUpdate,
): Promise<MerchantPolicyResponse> {
  return request<MerchantPolicyResponse>("/api/v1/merchant/policy", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getMerchantObjective(): Promise<MerchantObjectiveResponse> {
  return request<MerchantObjectiveResponse>("/api/v1/merchant/objective");
}

export function updateMerchantObjective(
  payload: MerchantObjectiveUpdate,
): Promise<MerchantObjectiveResponse> {
  return request<MerchantObjectiveResponse>("/api/v1/merchant/objective", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function reselectOptimisation(
  runId: string,
): Promise<OptimisationResponse> {
  return request<OptimisationResponse>(
    `/api/v1/optimisation/runs/${runId}/reselect`,
    { method: "POST" },
  );
}

export function qualifyIntent(
  intent: string,
  parserMode?: "rule_based" | "llm",
): Promise<QualifyResponse> {
  return request<QualifyResponse>("/api/v1/intent/qualify", {
    method: "POST",
    body: JSON.stringify({
      intent,
      parser_mode: parserMode,
    }),
  });
}

export function getQualificationVariant(
  runId: string,
  variantId: string,
): Promise<QualificationVariantDetail> {
  return request<QualificationVariantDetail>(
    `/api/v1/intent/qualification/${runId}/variants/${variantId}`,
  );
}

export function matchIntent(
  intent: string,
  parserMode?: "rule_based" | "llm",
  limit = 8,
): Promise<MatchResponse> {
  return request<MatchResponse>("/api/v1/match", {
    method: "POST",
    body: JSON.stringify({
      intent,
      parser_mode: parserMode,
      limit,
    }),
  });
}

export function generateOffers(payload: {
  intent?: string;
  match_run_id?: string;
  parser_mode?: "rule_based" | "llm";
  max_products?: number;
  status?: "FEASIBLE" | "REJECTED" | "ALL";
  limit?: number;
}): Promise<GenerateOffersResponse> {
  return request<GenerateOffersResponse>("/api/v1/offers/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getOfferRun(
  runId: string,
  params?: {
    product_id?: string;
    delivery?: string;
    warranty?: string;
    bundle?: string;
    returns?: string;
    status?: string;
    max_price_cents?: number;
    limit?: number;
    offset?: number;
  },
): Promise<OfferRunResponse> {
  const search = new URLSearchParams();
  if (params?.product_id) search.set("product_id", params.product_id);
  if (params?.delivery) search.set("delivery", params.delivery);
  if (params?.warranty) search.set("warranty", params.warranty);
  if (params?.bundle) search.set("bundle", params.bundle);
  if (params?.returns) search.set("returns", params.returns);
  if (params?.status) search.set("status", params.status);
  if (params?.max_price_cents != null) {
    search.set("max_price_cents", String(params.max_price_cents));
  }
  search.set("limit", String(params?.limit ?? 40));
  search.set("offset", String(params?.offset ?? 0));
  return request<OfferRunResponse>(`/api/v1/offers/runs/${runId}?${search}`);
}

export function getOffer(offerId: string): Promise<OfferDetailResponse> {
  return request<OfferDetailResponse>(`/api/v1/offers/${offerId}`);
}

export function runDecision(payload: {
  intent: string;
  parser_mode?: "rule_based" | "llm";
  buyer_profile?: BuyerProfile;
  max_products?: number;
}): Promise<DecisionResponse> {
  return request<DecisionResponse>("/api/v1/decision/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runOptimisation(payload: {
  offer_run_id: string;
  buyer_profile?: BuyerProfile;
}): Promise<OptimisationResponse> {
  return request<OptimisationResponse>("/api/v1/optimisation/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getNegotiation(sessionId: string): Promise<NegotiationResponse> {
  return request<NegotiationResponse>(`/api/v1/negotiations/${sessionId}`);
}

export function createNegotiation(payload: {
  intent: string;
  parser_mode?: "rule_based" | "llm";
  buyer_profile?: BuyerProfile;
  max_products?: number;
}): Promise<NegotiationResponse> {
  return request<NegotiationResponse>("/api/v1/negotiations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function postNegotiationTurn(
  sessionId: string,
  payload: {
    message?: string;
    action?: string;
    constraints?: Record<string, unknown>;
  },
): Promise<NegotiationResponse> {
  return request<NegotiationResponse>(`/api/v1/negotiations/${sessionId}/turns`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function simulateNegotiationBuyer(
  sessionId: string,
  mode: "BUDGET" | "URGENT" | "ASSURANCE" | "BALANCED" | "TRAVEL",
): Promise<NegotiationResponse> {
  return request<NegotiationResponse>(
    `/api/v1/negotiations/${sessionId}/simulate-buyer`,
    {
      method: "POST",
      body: JSON.stringify({ mode }),
    },
  );
}

export function acceptProposal(
  sessionId: string,
  payload: {
    proposal_id: string;
    idempotency_key: string;
    generate_recovery?: boolean;
  },
): Promise<AcceptProposalResponse> {
  return request<AcceptProposalResponse>(
    `/api/v1/negotiations/${sessionId}/accept`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function getTransaction(
  transactionId: string,
): Promise<AcceptProposalResponse> {
  return request<AcceptProposalResponse>(
    `/api/v1/transactions/${transactionId}`,
  );
}

export function setDemoInventory(payload: {
  sku?: string;
  variant_id?: string;
  units_available: number;
}): Promise<DemoStateResponse> {
  return request<DemoStateResponse>("/api/v1/demo/inventory", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function setDemoDeliveryCapacity(payload: {
  sku?: string;
  variant_id?: string;
  delivery_code?: string;
  available: boolean;
}): Promise<DemoStateResponse> {
  return request<DemoStateResponse>("/api/v1/demo/delivery-capacity", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function setDemoPolicy(payload: {
  minimum_margin_rate?: number;
  maximum_discount_rate?: number;
}): Promise<DemoStateResponse> {
  return request<DemoStateResponse>("/api/v1/demo/policy", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runArenaDuel(payload: {
  intent: string;
  buyer_profile?: BuyerProfile;
}): Promise<ArenaRunResponse> {
  return request<ArenaRunResponse>("/api/v1/arena/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createArenaBenchmark(payload: {
  mission_count: number;
  seed: number;
  strategies?: string[];
}): Promise<ArenaBenchmarkCreated> {
  return request<ArenaBenchmarkCreated>("/api/v1/arena/benchmarks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getArenaBenchmark(
  benchmarkId: string,
): Promise<ArenaBenchmarkResponse> {
  return request<ArenaBenchmarkResponse>(
    `/api/v1/arena/benchmarks/${benchmarkId}`,
  );
}

export async function getLatestArenaBenchmark(): Promise<ArenaBenchmarkResponse | null> {
  try {
    return await request<ArenaBenchmarkResponse>(
      "/api/v1/arena/benchmarks/latest",
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export function arenaBenchmarkExportUrl(
  benchmarkId: string,
  format: "json" | "csv",
): string {
  return `${API_BASE_URL}/api/v1/arena/benchmarks/${benchmarkId}/export?format=${format}`;
}

export function getLearningOverview(): Promise<LearningOverview> {
  return request<LearningOverview>("/api/v1/learning/overview");
}

export function generateLearningDataset(payload: {
  interaction_count_target: number;
  seed: number;
}): Promise<LearningDatasetSummary> {
  return request<LearningDatasetSummary>("/api/v1/learning/datasets/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function trainLearningModels(payload: {
  dataset_id: string;
  seed?: number;
}): Promise<LearningTrainResponse> {
  return request<LearningTrainResponse>("/api/v1/learning/train", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
