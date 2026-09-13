"use client";

import { useMemo, useState } from "react";

import { formatAudCents } from "@/lib/money";
import {
  QUALIFY_LIST_PREVIEW,
  humanizeExclusionReason,
  qualificationReasonCopy,
  rowSpecificReasons,
  sharedExclusionReason,
} from "@/lib/qualifyDisplay";
import type { QualifyResponse, VariantQualificationCard } from "@/types";

export function QualificationResults({
  detail,
}: {
  detail: QualifyResponse;
}) {
  const groups = [
    { key: "eligible", title: "Eligible", items: detail.eligible_products },
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
      {groups.map((group) => (
        <QualificationGroup
          key={group.key}
          title={group.title}
          items={group.items}
          truncated={"truncated" in group ? group.truncated : false}
        />
      ))}
    </div>
  );
}

function QualificationGroup({
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
    <div>
      <p className="type-small text-muted">
        {title} · {items.length}
        {truncated ? "+" : ""}
      </p>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-muted">None</p>
      ) : (
        <>
          {groupReason ? (
            <p className="mt-2 text-sm">
              <span className="text-muted">Shared reason</span>
              <span className="mx-2 text-muted">·</span>
              {qualificationReasonCopy(groupReason)}
            </p>
          ) : null}
          <ul className="mt-2">
            {visible.map((item) => {
              const extras = rowSpecificReasons(item, groupReason);
              return (
                <li
                  key={item.variant_id}
                  className="flex items-baseline justify-between gap-4 border-b border-line-muted py-1.5 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate">{item.product_name}</p>
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
    </div>
  );
}
