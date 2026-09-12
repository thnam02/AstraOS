import { API_BASE_URL } from "@/lib/config";
import type {
  CatalogueStatsResponse,
  HealthResponse,
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

export function getCatalogueStats(): Promise<CatalogueStatsResponse> {
  return request<CatalogueStatsResponse>("/api/v1/catalogue/stats");
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
