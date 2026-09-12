"use client";

import { useState } from "react";

import { Drawer } from "@/components/shared/Drawer";
import { EvidenceBadge } from "@/components/shared/EvidenceBadge";
import { conciseOfferReasons, commercialLevers, offerVsProductCopy } from "@/lib/decisionNarrative";
import { sourceBadge } from "@/lib/matchDisplay";
import { formatAudCents } from "@/lib/money";
import type {
  MerchantObjectiveSnapshot,
  ProofItem,
  PublicScoredOffer,
  RankedProductMatch,
  SelectionScore,
} from "@/types";

const GROUPS: { key: string; label: string }[] = [
  { key: "PRODUCT", label: "Product proof" },
  { key: "PRICE", label: "Price" },
  { key: "DELIVERY", label: "Delivery" },
  { key: "WARRANTY", label: "Warranty" },
  { key: "BUNDLE", label: "Bundle" },
  { key: "RETURNS", label: "Returns" },
  { key: "INVENTORY", label: "Inventory" },
];

export function RecommendedOffer({
  offer,
  explanation,
  onWhyDifferent,
  objective,
  selection,
  topMatch,
}: {
  offer: PublicScoredOffer;
  explanation: string[];
  onWhyDifferent?: () => void;
  objective?: MerchantObjectiveSnapshot | null;
  selection?: SelectionScore | null;
  topMatch?: RankedProductMatch | null;
}) {
  const reasons = conciseOfferReasons(explanation);
  const items = (offer.proof_bundle?.items ?? []).filter(
    (item) => !item.incomplete,
  );
  const [proofOpen, setProofOpen] = useState(false);
  const [whyOpen, setWhyOpen] = useState(false);
  const differ = Boolean(
    topMatch && topMatch.sku && offer.sku && topMatch.sku !== offer.sku,
  );

  return (
    <article className="space-y-4">
      <div>
        <p className="eyebrow" title="Complete commercial configuration selected by AstraOS.">
          Selected commercial offer
        </p>
        <h2 className="mt-2 text-[22px] font-semibold tracking-tight">
          {offer.product_name}
        </h2>
        <p className="font-mono text-[11px] text-muted">{offer.sku}</p>
        {objective ? (
          <p
            className="mt-2 text-[11px] text-muted"
            title="Selection from Pareto-efficient offers using the merchant's configured commercial objective."
          >
            Selected under {objective.mode.charAt(0)}
            {objective.mode.slice(1).toLowerCase()} objective
            {selection
              ? ` · score ${selection.score.toFixed(3)}`
              : ""}
          </p>
        ) : null}
        <p className="mt-2 font-mono text-3xl font-semibold tabular-nums">
          {formatAudCents(offer.pricing.total_price_cents)}
        </p>
        <ul className="mt-2 space-y-0.5 text-sm">
          {commercialLevers(offer).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <p
        className="text-xs text-muted"
        title="How strongly the product itself aligns with buyer intent."
      >
        Product match {Math.round(offer.product_fit * 100)} / 100
      </p>

      <dl className="space-y-2">
        <div>
          <dt
            className="eyebrow"
            title="Transparent cold-start score for the complete offer configuration."
          >
            Simulated buyer utility
          </dt>
          <dd className="font-mono text-3xl font-semibold tabular-nums">
            {offer.buyer_utility.toFixed(2)}
          </dd>
          <p className="text-[11px] text-muted">Cold-start score — not purchase probability.</p>
        </div>
        <div className="flex justify-between gap-3 text-sm">
          <dt
            className="text-muted"
            title="Estimated contribution from the complete commercial offer."
          >
            Merchant contribution
          </dt>
          <dd className="font-mono tabular-nums">
            {formatAudCents(offer.contribution_margin_cents)}
          </dd>
        </div>
        <div className="flex justify-between gap-3 text-sm">
          <dt className="text-muted">Intervention cost</dt>
          <dd className="font-mono tabular-nums">
            {formatAudCents(offer.incremental_intervention_cost_cents)}
          </dd>
        </div>
      </dl>

      {reasons.length ? (
        <div>
          <p className="eyebrow">Why this offer</p>
          <ul className="mt-2 space-y-1 text-sm">
            {reasons.map((reason) => (
              <li key={reason} className="flex gap-2">
                <span className="text-success">✓</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-3">
        {onWhyDifferent || differ ? (
          <button
            type="button"
            className="btn-quiet"
            onClick={() => {
              setWhyOpen(true);
              onWhyDifferent?.();
            }}
          >
            Why this product instead of #1?
          </button>
        ) : null}
        {items.length ? (
          <button type="button" className="btn-quiet" onClick={() => setProofOpen(true)}>
            Inspect proof
          </button>
        ) : null}
      </div>

      <OfferProofDrawer
        open={proofOpen}
        items={items}
        onClose={() => setProofOpen(false)}
      />
      <WhyDifferentDrawer
        open={whyOpen}
        offer={offer}
        topMatch={topMatch ?? null}
        items={items}
        onClose={() => setWhyOpen(false)}
      />
    </article>
  );
}

function OfferProofDrawer({
  open,
  items,
  onClose,
}: {
  open: boolean;
  items: ProofItem[];
  onClose: () => void;
}) {
  return (
    <Drawer open={open} title="Offer proof" onClose={onClose}>
      <div className="space-y-5">
        {GROUPS.map((group) => {
          const rows = items.filter((item) => (item.group ?? "PRODUCT") === group.key);
          if (!rows.length) return null;
          return (
            <section key={group.key}>
              <p className="eyebrow">{group.label}</p>
              <ul className="mt-2 space-y-2">
                {rows.map((item) => (
                  <ProofRow key={`${item.claim_key}-${String(item.value)}`} item={item} />
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </Drawer>
  );
}

function WhyDifferentDrawer({
  open,
  offer,
  topMatch,
  items,
  onClose,
}: {
  open: boolean;
  offer: PublicScoredOffer;
  topMatch: RankedProductMatch | null;
  items: ProofItem[];
  onClose: () => void;
}) {
  const commercial = items.filter((item) =>
    ["PRICE", "DELIVERY", "WARRANTY", "BUNDLE", "RETURNS"].includes(
      item.group ?? "",
    ),
  );
  return (
    <Drawer open={open} title="Product match vs selected offer" onClose={onClose}>
      <div className="space-y-3 text-sm">
        <p>{offerVsProductCopy(Boolean(topMatch && topMatch.sku !== offer.sku))}</p>
        {topMatch ? (
          <p>
            <span className="text-muted">Top product match </span>
            {topMatch.product_name}
          </p>
        ) : null}
        <p>
          <span className="text-muted">Selected commercial offer </span>
          {offer.product_name}
        </p>
        {commercial.length ? (
          <ul className="space-y-2">
            {commercial.map((item) => (
              <ProofRow key={`${item.claim_key}-${String(item.value)}`} item={item} />
            ))}
          </ul>
        ) : null}
      </div>
    </Drawer>
  );
}

function ProofRow({ item }: { item: ProofItem }) {
  const badge = sourceBadge(item.source_type, item.source_name);
  return (
    <li className="flex flex-wrap items-center justify-between gap-2">
      <span>
        {item.display_claim}
        {item.unit && !item.display_claim.includes(item.unit)
          ? ` ${item.unit}`
          : ""}
      </span>
      <EvidenceBadge source={badge} />
    </li>
  );
}
