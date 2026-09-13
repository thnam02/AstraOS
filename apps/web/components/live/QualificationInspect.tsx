"use client";

import { useMemo, useState } from "react";

import { Drawer } from "@/components/shared/Drawer";
import { qualifyIntent } from "@/lib/api";
import { formatAudCents } from "@/lib/money";
import {
  QUALIFY_LIST_PREVIEW,
  humanizeExclusionReason,
  qualificationReasonCopy,
  rowSpecificReasons,
  sharedExclusionReason,
} from "@/lib/qualifyDisplay";
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
        {detail ? <QualificationBody detail={detail} /> : null}
      </Drawer>
    </>
  );
}

function QualificationBody({ detail }: { detail: QualifyResponse }) {
  const groups = [
    { key: "satisfied", title: "Satisfied", items: detail.eligible_products },
    {
      key: "violated",
      title: "Violated",
      items: detail.rejected_products,
      truncated: detail.rejected_truncated,
    },
    {
      key: "unknown",
      title: "Unknown",
      items: detail.uncertain_products,
      truncated: detail.uncertain_truncated,
    },
  ] as const;

  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-3 gap-3 text-sm">
        {groups.map((group) => (
          <div key={group.key}>
            <dt className="type-small text-muted">{group.title}</dt>
            <dd className="mt-1 font-mono tabular-nums">{group.items.length}</dd>
          </div>
        ))}
      </dl>
      {groups.map((group) => (
        <Group
          key={group.key}
          title={group.title}
          items={group.items}
          truncated={"truncated" in group ? group.truncated : false}
        />
      ))}
    </div>
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
  const [showAll, setShowAll] = useState(false);
  const groupReason = useMemo(() => sharedExclusionReason(items), [items]);
  const visible = showAll ? items : items.slice(0, QUALIFY_LIST_PREVIEW);
  const hidden = items.length - visible.length;

  return (
    <section>
      <p className="eyebrow">
        {title} · {items.length}
        {truncated ? "+" : ""}
      </p>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-muted">None</p>
      ) : (
        <>
          {groupReason ? (
            <p className="mt-2 text-sm text-muted">
              <span className="text-ink">Why {title.toLowerCase()}?</span>{" "}
              {qualificationReasonCopy(groupReason)}
            </p>
          ) : null}
          <ul className="mt-2">
            {visible.map((item) => {
              const extras = rowSpecificReasons(item, groupReason);
              return (
                <li
                  key={item.variant_id}
                  className="flex items-baseline justify-between gap-4 border-b border-line py-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{item.product_name}</p>
                    <p className="font-mono text-[11px] text-muted">{item.sku}</p>
                    {extras.length ? (
                      <p className="mt-0.5 text-xs text-muted">
                        {extras
                          .slice(0, 2)
                          .map((reason) =>
                            humanizeExclusionReason(reason, {
                              includeObserved: true,
                            }),
                          )
                          .join(" · ")}
                      </p>
                    ) : null}
                  </div>
                  <p className="shrink-0 font-mono text-[11px] tabular-nums text-muted">
                    {formatAudCents(item.base_price_cents)}
                  </p>
                </li>
              );
            })}
          </ul>
          {hidden > 0 ? (
            <button
              type="button"
              className="btn-quiet mt-2"
              onClick={() => setShowAll(true)}
            >
              Show all {items.length}
            </button>
          ) : null}
        </>
      )}
    </section>
  );
}
