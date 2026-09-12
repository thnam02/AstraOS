export type HealthResponse = {
  status: string;
  service: string;
};

export type ConnectionStatus = "loading" | "connected" | "unavailable";

export type InventoryResponse = {
  id: string;
  variant_id: string;
  units_available: number;
  units_reserved: number;
  warehouse_code: string;
  updated_at: string;
};

export type DeliveryOptionResponse = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  delivery_days: number;
  merchant_cost_cents: number;
  customer_charge_cents: number;
  enabled: boolean;
  available: boolean;
  cutoff_time: string | null;
};

export type WarrantyOptionResponse = {
  id: string;
  code: string;
  name: string;
  months: number;
  merchant_cost_cents: number;
  customer_price_cents: number;
  enabled: boolean;
  available: boolean;
};

export type BundleOptionResponse = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  merchant_cost_cents: number;
  customer_price_cents: number;
  enabled: boolean;
  attributes: Record<string, unknown> | null;
  available: boolean;
};

export type ReturnPolicyResponse = {
  id: string;
  code: string;
  name: string;
  return_window_days: number;
  restocking_fee_rate: number | null;
  conditions: string | null;
  merchant_expected_cost_cents: number | null;
  enabled: boolean;
  available: boolean;
};

export type AttributeEvidenceResponse = {
  id: string;
  variant_id: string | null;
  attribute_name: string;
  value: unknown;
  source: {
    id: string;
    name: string;
    source_type: string;
    reference: string | null;
  };
  verification_status: string;
  observed_at: string;
  expires_at: string | null;
  is_stale: boolean;
};

export type VariantSummary = {
  id: string;
  sku: string;
  variant_name: string | null;
  currency: string;
  base_price_cents: number;
  cogs_cents: number;
  units_available: number;
  units_reserved: number;
  same_day_available: boolean;
  anc: boolean | null;
  battery_hours: number | null;
  is_active: boolean;
  has_missing_attributes: boolean;
};

export type ProductSummary = {
  id: string;
  name: string;
  brand: string;
  category: string;
  model_number: string | null;
  is_active: boolean;
  variant_count: number;
  variants: VariantSummary[];
};

export type ProductListResponse = {
  items: ProductSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type ProductVariantDetail = {
  id: string;
  product_id: string;
  sku: string;
  variant_name: string | null;
  currency: string;
  base_price_cents: number;
  cogs_cents: number;
  attributes: Record<string, unknown>;
  is_active: boolean;
  inventory: InventoryResponse | null;
  delivery_options: DeliveryOptionResponse[];
  warranty_options: WarrantyOptionResponse[];
  bundle_options: BundleOptionResponse[];
  return_policies: ReturnPolicyResponse[];
  evidence: AttributeEvidenceResponse[];
};

export type ProductDetail = {
  product: {
    id: string;
    name: string;
    brand: string;
    category: string;
    description: string | null;
    model_number: string | null;
    manufacturer: string | null;
    is_active: boolean;
  };
  variants: ProductVariantDetail[];
};

export type CatalogueStatsResponse = {
  products: number;
  variants: number;
  in_stock_variants: number;
  out_of_stock_variants: number;
  same_day_capable: number;
  missing_attribute_variants: number;
  brands: number;
  categories: string[];
  evidence_records: number;
};

export type MerchantPolicyResponse = {
  id: string;
  name: string;
  is_active: boolean;
  minimum_margin_rate: number;
  maximum_discount_rate: number;
  delivery_subsidy_enabled: boolean;
  warranty_upgrade_enabled: boolean;
  bundle_enabled: boolean;
  flexible_returns_enabled: boolean;
  loyalty_enabled: boolean;
};

export type MerchantPolicyUpdate = {
  minimum_margin_rate?: number;
  maximum_discount_rate?: number;
  delivery_subsidy_enabled?: boolean;
  warranty_upgrade_enabled?: boolean;
  bundle_enabled?: boolean;
  flexible_returns_enabled?: boolean;
};
