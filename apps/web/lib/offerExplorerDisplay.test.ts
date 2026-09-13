import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  filterChipLabel,
  offerExplorerColumns,
  offerGroupConstants,
  offerPricingBreakdown,
  sortOfferConfigurations,
} from "./offerExplorerDisplay";
import type { PublicOffer } from "@/types";

function offer(partial: {
  id: string;
  productId?: string;
  price?: number;
  total?: number;
  intervention?: number;
  delivery?: string;
  warrantyMonths?: number;
  warrantyCode?: string;
  returnsDays?: number;
  status?: string;
  deliveryCharge?: number;
  warrantyPrice?: number;
  bundlePrice?: number;
}): PublicOffer {
  return {
    offer_id: partial.id,
    product: {
      variant_id: "v1",
      product_id: partial.productId ?? "p1",
      sku: "SKU-1",
      name: "Atlas Cabin 72",
      brand: "Atlas",
      variant_name: null,
    },
    pricing: {
      product_price_cents: partial.price ?? 18108,
      base_price_cents: partial.price ?? 18108,
      adjustment_cents: 0,
      adjustment_type: "NONE",
      delivery_charge_cents: partial.deliveryCharge ?? 1000,
      warranty_price_cents: partial.warrantyPrice ?? 0,
      bundle_price_cents: partial.bundlePrice ?? 0,
      total_price_cents: partial.total ?? 19108,
      currency: "AUD",
    },
    delivery: {
      code: partial.delivery ?? "SAME_DAY",
      name: "Same Day",
      days: 0,
    },
    warranty: {
      code: partial.warrantyCode ?? "STD_12",
      name: "12-month",
      months: partial.warrantyMonths ?? 12,
    },
    bundle: { code: "NONE", name: null },
    returns: {
      code: "STD_30",
      name: "30-day",
      window_days: partial.returnsDays ?? 30,
    },
    proof: [],
    expires_at: null,
    feasibility_status: partial.status ?? "FEASIBLE",
    construction_status: "BUILT",
    rejection_reasons: [],
    direct_intervention_cost_cents: partial.intervention ?? 1200,
    bundle_relevance: null,
  };
}

describe("offer explorer columns", () => {
  it("hides constant product price, delivery, and status", () => {
    const rows = [
      offer({ id: "a", warrantyMonths: 12 }),
      offer({ id: "b", warrantyMonths: 24, total: 20108 }),
    ];
    assert.deepEqual(offerExplorerColumns(rows, "FEASIBLE"), {
      productPrice: false,
      delivery: false,
      status: false,
    });
  });

  it("keeps varying dimensions in the table", () => {
    const rows = [
      offer({ id: "a", price: 18108, delivery: "SAME_DAY", status: "FEASIBLE" }),
      offer({
        id: "b",
        price: 19000,
        delivery: "EXPRESS",
        status: "REJECTED",
      }),
    ];
    assert.deepEqual(offerExplorerColumns(rows, "ALL"), {
      productPrice: true,
      delivery: true,
      status: true,
    });
  });
});

describe("offer group constants", () => {
  it("surfaces shared product context", () => {
    const constants = offerGroupConstants([
      offer({ id: "a" }),
      offer({ id: "b", total: 20000 }),
    ]);
    assert.equal(constants?.name, "Atlas Cabin 72");
    assert.equal(constants?.productPriceCents, 18108);
    assert.ok(constants?.delivery);
    assert.equal(constants?.status, "FEASIBLE");
  });
});

describe("sort offer configurations", () => {
  it("sorts by customer total without inventing ranks", () => {
    const sorted = sortOfferConfigurations(
      [
        offer({ id: "b", total: 22000 }),
        offer({ id: "a", total: 19108 }),
      ],
      "total",
      "asc",
    );
    assert.deepEqual(
      sorted.map((row) => row.offer_id),
      ["a", "b"],
    );
  });

  it("keeps default order when requested", () => {
    const input = [offer({ id: "b" }), offer({ id: "a" })];
    const sorted = sortOfferConfigurations(input, "default");
    assert.deepEqual(
      sorted.map((row) => row.offer_id),
      ["b", "a"],
    );
  });
});

describe("pricing breakdown", () => {
  it("only includes supported pricing components", () => {
    const rows = offerPricingBreakdown(
      offer({
        id: "a",
        deliveryCharge: 1000,
        warrantyPrice: 2500,
        bundlePrice: 0,
      }),
    );
    assert.deepEqual(
      rows.map((row) => row.label),
      ["Product", "Delivery", "Warranty"],
    );
  });
});

describe("filter chips", () => {
  it("labels status filters clearly", () => {
    assert.equal(filterChipLabel("status", "FEASIBLE"), "Status: feasible");
  });
});
