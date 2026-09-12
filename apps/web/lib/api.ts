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
