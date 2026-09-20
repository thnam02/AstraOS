"use client";

import { useMemo, useState } from "react";

import { AstraPanel } from "@/components/astra";

import { StageTabs } from "./StageShell";

import { formatAudCents } from "@/lib/money";
import {
  humanizeExclusionReason,
  qualificationReasonCopy,
  rowSpecificReasons,
  sharedExclusionReason,
} from "@/lib/qualifyDisplay";
import type { QualifyResponse, VariantQualificationCard } from "@/types";

export function QualificationResults({
  detail,
  layout = "tabs",
}: {
  detail: QualifyResponse;
  layout?: "tabs" | "columns";
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

  if (layout === "columns") {
    return (
      <div
        className="qualification-columns grid gap-3 lg:grid-cols-3"
        aria-label="Qualification results"
      >
        {groups.map((group) => (
          <AstraPanel key={group.key} className="min-w-0">
            <QualificationGroup
              title={group.title}
              items={group.items}
              truncated={"truncated" in group ? group.truncated : false}
              pageSize={4}
              expanded
            />
          </AstraPanel>
        ))}
      </div>
    );
  }

  return (
    <StageTabs
      label="Qualification outcomes"
      items={groups.map((group) => ({
        label: `${group.title} (${group.items.length}${"truncated" in group && group.truncated ? "+" : ""})`,
        content: (
          <QualificationGroup
            title={group.title}
            items={group.items}
            truncated={"truncated" in group ? group.truncated : false}
          />
        ),
      }))}
    />
  );
}

function QualificationGroup({
  title,
  items,
  truncated,
  pageSize = 4,
  expanded = false,
}: {
  title: string;
  items: VariantQualificationCard[];
  truncated?: boolean;
  pageSize?: number;
  expanded?: boolean;
}) {
  const [page, setPage] = useState(0);
  const lastPage = Math.max(0, Math.ceil(items.length / pageSize) - 1);
  const currentPage = Math.min(page, lastPage);
  const groupReason = useMemo(() => sharedExclusionReason(items), [items]);
  const visible = items.slice(
    currentPage * pageSize,
    (currentPage + 1) * pageSize,
  );

  return (
    <div className={expanded ? "flex h-full flex-col" : undefined}>
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
          <ul className={expanded ? "mt-2 grid flex-1 auto-rows-fr" : "mt-2"}>
            {visible.map((item) => {
              const extras = rowSpecificReasons(item, groupReason);
              return (
                <li
                  key={item.variant_id}
                  className={
                    expanded
                      ? "flex items-center justify-between gap-4 border-b border-line-muted py-2 text-sm"
                      : "flex items-baseline justify-between gap-4 border-b border-line-muted py-1.5 text-sm"
                  }
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
          {lastPage > 0 ? (
            <nav
              className="mt-3 flex items-center justify-between gap-2 text-xs"
              aria-label={`${title} pages`}
            >
              <button
                type="button"
                className="btn-quiet disabled:opacity-40"
                disabled={currentPage === 0}
                onClick={() => setPage(currentPage - 1)}
              >
                Previous
              </button>
              <span className="text-muted">
                {currentPage * pageSize + 1}–
                {Math.min((currentPage + 1) * pageSize, items.length)} of{" "}
                {items.length}
                {truncated ? "+" : ""}
              </span>
              <button
                type="button"
                className="btn-quiet disabled:opacity-40"
                disabled={currentPage === lastPage}
                onClick={() => setPage(currentPage + 1)}
              >
                Next
              </button>
            </nav>
          ) : null}
        </>
      )}
    </div>
  );
}
