"use client";

import { useState } from "react";

import { Drawer } from "@/components/shared/Drawer";
import { qualifyIntent } from "@/lib/api";
import { formatAudCents } from "@/lib/money";
import type { QualifyResponse, VariantQualificationCard } from "@/types";

export function QualificationInspect({
  intentText,
  parserMode,
}: {
  intentText: string;
  parserMode: "rule_based" | "llm";
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState<QualifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function inspect() {
    setOpen(true);
    if (detail || busy) return;
    setBusy(true);
    setError(null);
    try {
      setDetail(await qualifyIntent(intentText, parserMode));
    } catch {
      setError("Could not load qualification detail.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button type="button" className="btn-quiet" onClick={() => void inspect()}>
        Inspect qualification
      </button>
      <Drawer open={open} title="Qualification" onClose={() => setOpen(false)}>
        {busy ? <p className="text-sm text-muted">Loading eligibility…</p> : null}
        {error ? <p className="text-sm text-danger">{error}</p> : null}
        {detail ? (
          <div className="space-y-5">
            <Group title="Satisfied" items={detail.eligible_products} />
            <Group title="Violated" items={detail.rejected_products} truncated={detail.rejected_truncated} />
            <Group
              title="Unknown"
              items={detail.uncertain_products}
              truncated={detail.uncertain_truncated}
            />
          </div>
        ) : null}
      </Drawer>
    </>
  );
}

function Group({
  title,
  items,
  truncated,
}: {
  title: string;
  items: VariantQualificationCard[];
  truncated?: boolean;
}) {
  return (
    <section>
      <p className="eyebrow">
        {title} · {items.length}
        {truncated ? "+" : ""}
      </p>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-muted">None</p>
      ) : (
        <ul className="mt-2 max-h-64 space-y-2 overflow-y-auto text-sm">
          {items.slice(0, 40).map((item) => (
            <li key={item.variant_id} className="border-b border-line py-2">
              <p className="font-medium">{item.product_name}</p>
              <p className="font-mono text-[11px] text-muted">
                {item.sku} · {formatAudCents(item.base_price_cents)}
              </p>
              {item.exclusion_reasons.length ? (
                <p className="mt-1 text-xs text-muted">
                  {item.exclusion_reasons.slice(0, 2).join(" · ")}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
