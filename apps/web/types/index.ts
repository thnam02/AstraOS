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
  parser_metadata?: {
    parser_requested: string;
    parser_used: string;
    fallback_used: boolean;
    fallback_reason: string | null;
    provider: string | null;
    model: string | null;
    prompt_version: string | null;
    schema_version: string | null;
    repair_count: number;
    latency_ms: number | null;
    input_tokens: number | null;
    output_tokens: number | null;
    total_tokens: number | null;
  } | null;
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

export type PublicOffer = {
  offer_id: string;
  product: {
    variant_id: string;
    product_id: string;
    sku: string;
    name: string;
    brand: string;
    variant_name: string | null;
  };
  pricing: {
    product_price_cents: number;
    base_price_cents: number;
    adjustment_cents: number;
    adjustment_type: string;
    delivery_charge_cents: number;
    warranty_price_cents: number;
    bundle_price_cents: number;
    total_price_cents: number;
    currency: string;
  };
  delivery: { code: string; name: string; days: number };
  warranty: { code: string; name: string; months: number };
  bundle: { code: string; name: string | null } | null;
  returns: { code: string; name: string | null; window_days: number | null } | null;
  proof: {
    type: string;
    value: unknown;
    source: string;
    source_name: string | null;
    evidence_id: string | null;
    updated_at: string | null;
  }[];
  expires_at: string | null;
  feasibility_status: string;
  construction_status: string;
  rejection_reasons: { code: string; message: string }[];
  direct_intervention_cost_cents: number;
  bundle_relevance: {
    code: string;
    name: string;
    triggered_by: string[];
    variant_compatible: boolean;
    merchant_available: boolean;
  } | null;
};

export type GenerateOffersResponse = {
  offer_run_id: string;
  match_run_id: string | null;
  intent: ShoppingIntent;
  input: { matched_products: number };
  summary: {
    estimated_candidates: number;
    generated_candidates: number;
    feasible_candidates: number;
    rejected_candidates: number;
    pruning_reason: string | null;
    rejection_distribution: Record<string, number>;
  };
  dimensions: {
    price_options: number;
    delivery_options: number;
    warranty_options: number;
    bundle_options: number;
    return_options: number;
  };
  timing: {
    matching_load_ms: number;
    dimension_load_ms: number;
    combination_generation_ms: number;
    feasibility_filter_ms: number;
    persistence_ms: number;
    total_ms: number;
  };
  offers: PublicOffer[];
  truncated: boolean;
};

export type OfferRunResponse = {
  offer_run_id: string;
  match_run_id: string | null;
  intent: ShoppingIntent;
  summary: GenerateOffersResponse["summary"];
  dimensions: GenerateOffersResponse["dimensions"];
  timing: Record<string, number>;
  created_at: string;
  completed_at: string | null;
  offers: PublicOffer[];
  total_offers: number;
  limit: number;
  offset: number;
};

export type OfferDetailResponse = {
  offer: Record<string, unknown>;
  public: PublicOffer;
};

export type BuyerProfile =
  | "INTENT_ADAPTED"
  | "BALANCED"
  | "URGENT_TRAVELLER"
  | "BUDGET_SHOPPER"
  | "ASSURANCE_BUYER"
  | "QUALITY_FIRST";

export type PublicScoredOffer = {
  offer_id: string;
  product_name: string;
  brand: string;
  sku: string;
  variant_id: string;
  pricing: { product_price_cents: number; total_price_cents: number; currency: string };
  delivery: { code: string; name: string; days: number };
  warranty: { code: string; name: string; months: number };
  bundle: { code: string; name: string | null } | null;
  returns: { code: string; window_days: number | null } | null;
  contribution_margin_cents: number;
  contribution_margin_rate: number;
  incremental_intervention_cost_cents: number;
  buyer_utility: number;
  utility_trace: {
    components: { component: string; fit: number; weight: number; weighted: number }[];
    total: number;
  };
  policy_safe: boolean;
  policy_rejection_codes: string[];
  is_pareto_efficient: boolean;
  dominated_by_offer_id: string | null;
  is_recommended: boolean;
  is_baseline: boolean;
  product_fit: number;
  learned_synthetic_score?: number | null;
  learned_score_label?: string | null;
};

export type PlotPoint = {
  offer_id: string;
  product_name: string;
  sku: string;
  total_price_cents: number;
  delivery_code: string;
  warranty_code: string;
  bundle_code: string | null;
  return_policy_code: string | null;
  buyer_utility: number;
  contribution_margin_cents: number;
  intervention_cost_cents: number;
  is_pareto_efficient: boolean;
  is_recommended: boolean;
};

export type CounterfactualRow = {
  lever: string;
  label: string;
  offer_id: string | null;
  policy_safe: boolean;
  buyer_utility: number;
  delta_utility: number;
  contribution_margin_cents: number;
  delta_contribution_cents: number;
  incremental_intervention_cost_cents: number;
  intervention_efficiency: number | null;
  total_price_cents: number;
  delivery_code: string;
  warranty_code: string;
  bundle_code: string | null;
  return_policy_code: string | null;
};

export type OptimisationResponse = {
  optimisation_run_id: string;
  offer_run_id: string;
  match_run_id: string | null;
  summary: {
    offers_considered: number;
    policy_safe: number;
    policy_rejected: number;
    pareto_efficient: number;
  };
  buyer_model: {
    type: string;
    profile_id: string;
    weights: Record<string, number>;
    disclaimer: string;
  };
  timing: {
    economics_ms: number;
    policy_filter_ms: number;
    utility_ms: number;
    pareto_ms: number;
    selection_ms: number;
    counterfactual_ms: number;
    persistence_ms: number;
    total_optimisation_ms: number;
  };
  recommended_offer: PublicScoredOffer | null;
  pareto_offers: PublicScoredOffer[];
  alternative_pareto_offers: PublicScoredOffer[];
  plot_points: PlotPoint[];
  counterfactuals: CounterfactualRow[];
  comparisons: {
    role: string;
    offer_id: string | null;
    label: string;
    buyer_utility: number | null;
    contribution_margin_cents: number | null;
    policy_safe: boolean;
  }[];
  explanation: string[];
  failure: {
    code: string;
    message: string;
    requested_max_price_cents: number | null;
    lowest_constructed_price_cents: number | null;
    rejection_distribution: Record<string, number>;
  } | null;
};

export type DecisionResponse = {
  match: MatchResponse;
  construction: GenerateOffersResponse;
  optimisation: OptimisationResponse;
};

export type MerchantProposal = {
  proposal_id: string;
  negotiation_session_id: string;
  version: number;
  proposal_type: string;
  outcome: string;
  offer_id: string | null;
  offer: PublicScoredOffer | null;
  reason_codes: string[];
  explanation: string[];
  next_allowed_actions: string[];
  compromise: Record<string, number | string> | null;
  expires_at: string | null;
  created_at: string | null;
};

export type NegotiationTurn = {
  turn_id: string;
  turn_number: number;
  actor: string;
  raw_message: string | null;
  structured_action: string;
  structured_payload: Record<string, unknown>;
  related_offer_id: string | null;
  created_at: string;
};

export type NegotiationResponse = {
  session_id: string;
  state: string;
  proposal: MerchantProposal | null;
  previous_proposal: MerchantProposal | null;
  turns: NegotiationTurn[];
  proposals: MerchantProposal[];
  commercial: {
    minimum_margin_rate: number;
    maximum_discount_rate: number;
    inventory_units: number | null;
    expires_at: string | null;
    current_sku: string | null;
  } | null;
  timing: {
    message_interpretation_ms: number;
    delta_application_ms: number;
    reoptimisation_ms: number;
    proposal_generation_ms: number;
    total_turn_ms: number;
  } | null;
  events: { type: string; at: string; state: string }[];
  match?: MatchResponse | null;
  construction?: GenerateOffersResponse | null;
  optimisation?: OptimisationResponse | null;
};

export type RevalidationCheck = {
  check: string;
  status: "PASS" | "FAIL";
  available_units?: number | null;
  observed?: string | number | null;
  message?: string | null;
};

export type AcceptProposalResponse = {
  transaction_id: string;
  state: string;
  negotiation_state: string | null;
  proposal_id: string;
  offer_id: string | null;
  revalidation: {
    status: string;
    checks: RevalidationCheck[];
    failure_codes: string[];
    current_state_snapshot: Record<string, unknown>;
    validated_at: string | null;
  } | null;
  reservation: {
    reservation_id: string;
    status: string;
    variant_id: string | null;
    quantity: number | null;
  } | null;
  order: {
    order_id: string;
    order_number: string;
    status: string;
    sku: string;
    product_name: string;
    quantity: number;
    product_price_cents: number;
    delivery_charge_cents: number;
    warranty_price_cents: number;
    bundle_price_cents: number;
    total_amount_cents: number;
    currency: string;
    delivery_code: string | null;
    warranty_code: string | null;
    bundle_code: string | null;
    return_policy_code: string | null;
    warranty_months: number | null;
    payment_mode: string;
    payment_status: string;
    confirmation: Record<string, unknown>;
    created_at: string | null;
    confirmed_at: string | null;
  } | null;
  failure_codes: string[];
  next_actions: string[];
  recovery_proposal: MerchantProposal | null;
  timing: {
    revalidation_ms: number;
    reservation_ms: number;
    order_creation_ms: number;
    total_transaction_ms: number;
  } | null;
  events: { type: string; at: string; state: string }[];
  lineage: Record<string, unknown>;
};

export type ArenaStrategyName =
  | "DEFAULT"
  | "ALWAYS_DISCOUNT"
  | "CHEAPEST_ELIGIBLE"
  | "SEMANTIC_ONLY"
  | "ASTRAOS";

export type ArenaStrategyResponse = {
  strategy_name: string;
  product_id: string | null;
  variant_id: string | null;
  offer_id: string | null;
  sku: string | null;
  product_name: string | null;
  total_customer_price_cents: number | null;
  currency: string;
  delivery: string | null;
  delivery_days: number | null;
  warranty: string | null;
  warranty_months: number | null;
  bundle: string | null;
  returns: string | null;
  buyer_utility: number | null;
  merchant_contribution_cents: number | null;
  intervention_cost_cents: number | null;
  hard_constraints_satisfied: boolean;
  policy_safe: boolean;
  transaction_possible: boolean;
  failure_reason: string | null;
  utility_trace: {
    components: { component: string; fit: number; weight: number; weighted: number }[];
    total: number;
    version: string;
  } | null;
  used_pareto: boolean;
  used_max_discount: boolean;
  is_cheapest_in_space: boolean;
};

export type ArenaRunResponse = {
  arena_run_id: string;
  mission_id: string;
  buyer_profile: string;
  strategies: { name: string; response: ArenaStrategyResponse }[];
  buyer_selection: {
    selected_strategy: string | null;
    selected_offer_id: string | null;
    simulated_utility: number | null;
    no_purchase: boolean;
    reason: string;
    tie_break: string | null;
  };
  explanation: {
    profile_id?: string;
    profile_label?: string;
    weights?: Record<string, number>;
    reasons?: string[];
  };
  disclaimer: string;
  created_at: string;
};

export type ArenaStrategyMetrics = {
  strategy_name: string;
  missions: number;
  wins: number;
  selection_rate: number;
  avg_buyer_utility: number | null;
  avg_contribution_when_selected: number | null;
  contribution_per_opportunity_cents: number;
  avg_intervention_cost_cents: number | null;
  hard_constraint_violation_rate: number;
  policy_violation_rate: number;
  no_offer_rate: number;
  transaction_completion_rate: number;
};

export type ArenaSegmentMetrics = {
  scenario_tag: string;
  buyer_profile: string;
  strategy_name: string;
  missions: number;
  wins: number;
  selection_rate: number;
  avg_buyer_utility: number | null;
  avg_contribution_cents: number | null;
};

export type ArenaBenchmarkCreated = {
  benchmark_id: string;
  status: string;
  mission_count: number;
  seed: number;
  disclaimer: string;
};

export type ArenaBenchmarkResponse = {
  benchmark_id: string;
  status: string;
  seed: number;
  mission_count: number;
  strategies: string[];
  buyer_model_version: string;
  merchant_policy_version: string;
  started_at: string;
  completed_at: string | null;
  summary: {
    no_purchase_rate?: number;
    pairwise?: {
      left: string;
      right: string;
      left_wins: number;
      right_wins: number;
      no_purchase_or_other: number;
    }[];
  };
  strategy_metrics: ArenaStrategyMetrics[];
  segment_metrics: ArenaSegmentMetrics[];
  pairwise: {
    left: string;
    right: string;
    left_wins: number;
    right_wins: number;
    no_purchase_or_other: number;
  }[];
  timing: Record<string, number>;
  config: Record<string, unknown>;
  disclaimer: string;
};

export type LearningDatasetSummary = {
  dataset_id: string;
  seed: number;
  interaction_count: number;
  positive_count: number;
  negative_count: number;
  feature_schema_version: string;
  source_types: string[];
  metadata: {
    audit?: {
      buyer_profiles?: Record<string, number>;
      scenario_tags?: Record<string, number>;
      deliveries?: Record<string, number>;
      positive_rate?: number;
    };
    build_ms?: number;
    mission_count?: number;
  };
  disclaimer: string;
  created_at: string;
};

export type LearningModelSummary = {
  model_id: string;
  name: string;
  algorithm: string;
  status: string;
  training_data_source: string;
  train_size: number;
  validation_size: number;
  test_size: number;
  metrics: {
    classification?: Record<string, number>;
    ranking?: Record<string, number>;
    calibration?: { low: number; high: number; predicted: number; observed: number; count: number }[];
  };
  disclaimer: string;
  created_at: string;
};

export type LearningTrainResponse = {
  training_run_id: string;
  selected_algorithm: string;
  reports: Record<
    string,
    {
      classification: Record<string, number>;
      ranking: Record<string, number>;
      calibration: { low: number; high: number; predicted: number; observed: number; count: number }[];
    }
  >;
  ablations: Record<string, { classification: Record<string, number>; ranking: Record<string, number> }>;
  hero_mission: {
    group_id?: string;
    offers?: {
      price_cents: number;
      delivery_days: number;
      warranty_months: number;
      cold_start_utility: number;
      learned_score: number;
      selected: boolean;
    }[];
    note?: string;
  };
  disclaimer: string;
};

export type LearningOverview = {
  disclaimer: string;
  maturity: { id: string; label: string; state: string }[];
  dataset: LearningDatasetSummary | null;
  models: LearningModelSummary[];
  sample_interactions: {
    intent: string | null;
    profile: string | null;
    price_cents: number;
    delivery: string | null;
    warranty: string | null;
    outcome: string;
    source: string;
  }[];
  latest_training: {
    selected?: string | null;
    reports?: LearningTrainResponse["reports"];
    ablations?: LearningTrainResponse["ablations"];
    hero_mission?: LearningTrainResponse["hero_mission"];
    timing?: Record<string, number>;
  } | null;
  associations: { feature: string; coefficient: number }[];
};

export type DemoStateResponse = {
  sku: string;
  variant_id: string;
  units_available: number;
  units_reserved: number;
  sellable_units: number;
  delivery_code: string | null;
  delivery_available: boolean | null;
  minimum_margin_rate: number;
  note: string;
};
