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

export type ConstraintStatus = "SATISFIED" | "VIOLATED" | "UNKNOWN";

export type HardConstraint = {
  id: string;
  field: string;
  operator: string;
  value: unknown;
  unit: string | null;
  source_phrase: string;
  normalized_value: unknown;
  importance: "MANDATORY";
};

export type SoftPreference = {
  id: string;
  field: string;
  direction: "MAXIMIZE" | "MINIMIZE";
  importance: number;
  source_phrase: string;
};

export type IntentAmbiguity = {
  source_phrase: string;
  reason: string;
  suggested_resolution: string | null;
  appears_mandatory: boolean;
};

export type ShoppingIntent = {
  raw_text: string;
  category: string | null;
  hard_constraints: HardConstraint[];
  soft_preferences: SoftPreference[];
  context_tags: string[];
  context_items: {
    label: string;
    importance: number;
    source_phrase: string;
    confidence: number | null;
  }[];
  desired_outcomes: {
    label: string;
    importance: number;
    source_phrase: string;
    confidence: number | null;
  }[];
  values: {
    field: string;
    direction: "MAXIMIZE" | "MINIMIZE";
    importance: number;
    source_phrase: string;
  }[];
  tradeoffs: {
    preferred_dimension: string;
    over_dimension: string;
    strength: number;
    source_phrase: string;
  }[];
  unsupported_semantic_needs: {
    label: string;
    source_phrase: string;
    reason: string;
  }[];
  ambiguities: IntentAmbiguity[];
  parser_type: string;
  parser_version: string;
  status: "READY" | "NEEDS_CLARIFICATION" | "UNSUPPORTED";
};

export type RankedProductMatch = {
  product_id: string;
  variant_id: string;
  sku: string;
  product_name: string;
  brand: string;
  variant_name: string | null;
  base_price_cents: number;
  rank: number;
  semantic_similarity: number;
  product_fit: number;
  context_fit: number;
  preference_fit: number;
  evidence_coverage: number;
  overall_semantic_fit: number;
  matched_needs: string[];
  unsupported_needs: string[];
  reasons: {
    need: string;
    kind: string;
    facts: {
      attribute: string;
      value: unknown;
      display: string;
      evidence_id: string | null;
      source_name: string | null;
    }[];
  }[];
  evidence: {
    attribute: string;
    value: unknown;
    display: string;
    evidence_id: string | null;
    source_name: string | null;
  }[];
};

export type MatchResponse = {
  run_id: string;
  status: ShoppingIntent["status"];
  intent: ShoppingIntent;
  qualification: {
    variants_checked: number;
    eligible: number;
    violated: number;
    uncertain: number;
  };
  semantic_matching: {
    model: string;
    document_version: string;
    matches: RankedProductMatch[];
  };
  timing: {
    intent_parse_ms: number;
    qualification_ms: number;
    embedding_ms: number;
    rerank_ms: number;
    total_ms: number;
  };
};

export type ConstraintEvaluation = {
  constraint_id: string;
  field: string;
  operator: string;
  expected_value: unknown;
  observed_value: unknown;
  status: ConstraintStatus;
  reason: string;
  source_reference: string | null;
  source_name: string | null;
  evidence_id: string | null;
  evidence_freshness: string | null;
  verification_status: string | null;
  observed_at: string | null;
  expires_at: string | null;
  supporting_detail: string | null;
};

export type VariantQualificationCard = {
  product_id: string;
  variant_id: string;
  sku: string;
  product_name: string;
  brand: string;
  variant_name: string | null;
  base_price_cents: number;
  eligible: boolean;
  outcome: "eligible" | "rejected" | "uncertain";
  violated_count: number;
  unknown_count: number;
  satisfied_count: number;
  exclusion_reasons: string[];
  evaluations: ConstraintEvaluation[];
};

export type QualifyResponse = {
  run_id: string;
  status: ShoppingIntent["status"];
  intent: ShoppingIntent;
  summary: {
    variants_checked: number;
    eligible: number;
    violated: number;
    uncertain: number;
  };
  timing: {
    parse_ms: number;
    eligibility_ms: number;
    total_ms: number;
  };
  eligible_products: VariantQualificationCard[];
  uncertain_products: VariantQualificationCard[];
  rejected_products: VariantQualificationCard[];
  rejected_truncated: boolean;
  uncertain_truncated: boolean;
};

export type QualificationVariantDetail = {
  run_id: string;
  variant: VariantQualificationCard;
};
