"use client";

import { useEffect, useMemo, useState } from "react";

import { Drawer } from "@/components/shared/Drawer";
import { EvidenceBadge } from "@/components/shared/EvidenceBadge";
import { contextLabel } from "@/lib/intent";
import { matchScoreDisplay } from "@/lib/decisionNarrative";
import {
  displayedCoverage,
  factValue,
  prettyFactDisplay,
  primaryReasons,
  proofItems,
  remainingSignalCount,
  sourceBadge,
  tradeOffLine,
} from "@/lib/matchDisplay";
import { formatAudCents } from "@/lib/money";
import type { RankedProductMatch } from "@/types";

export function MatchList({
  matches,
  inspectNonce = 0,
  compareNonce = 0,
}: {
  matches: RankedProductMatch[];
  inspectNonce?: number;
  compareNonce?: number;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [inspect, setInspect] = useState<RankedProductMatch | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    if (!inspectNonce) return;
    const top = matches[0];
    if (!top) return;
    setExpanded(top.variant_id);
    setInspect(top);
  }, [inspectNonce, matches]);

  useEffect(() => {
    if (!compareNonce) return;
    const ids = matches.slice(0, 2).map((item) => item.variant_id);
    if (ids.length < 2) return;
    setCompareIds(ids);
    setCompareOpen(true);
  }, [compareNonce, matches]);

  const compareSet = matches.filter((item) => compareIds.includes(item.variant_id));
  const visible = showAll ? matches : matches.slice(0, 3);

  function toggleCompare(id: string) {
    setCompareIds((current) => {
      if (current.includes(id)) return current.filter((item) => item !== id);
      if (current.length >= 3) return current;
      return [...current, id];
    });
  }

  if (!matches.length) {
    return <p className="text-sm text-muted">No eligible products to rank.</p>;
  }

  return (
    <div className="space-y-1">
      {visible.map((match) => {
        const open = match.variant_id === expanded;
        if (open) {
          return (
            <ExpandedMatch
              key={match.variant_id}
              match={match}
              peers={matches}
              compared={compareIds.includes(match.variant_id)}
              onInspect={() => setInspect(match)}
              onCompare={() => toggleCompare(match.variant_id)}
              onCollapse={() => setExpanded(null)}
            />
          );
        }
        return (
          <CompactMatch
            key={match.variant_id}
            match={match}
            peers={matches}
            compared={compareIds.includes(match.variant_id)}
            onExpand={() => setExpanded(match.variant_id)}
            onCompare={() => toggleCompare(match.variant_id)}
          />
        );
      })}

      {matches.length > 3 ? (
        <button
          type="button"
          className="btn-quiet mt-2"
          onClick={() => setShowAll((current) => !current)}
          aria-expanded={showAll}
        >
          {showAll
            ? "Show top 3 products"
            : `View all ${matches.length} products`}
        </button>
      ) : null}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-muted">
          {compareIds.length
            ? `${compareIds.length} selected for comparison`
            : "Select up to 3 matches to compare"}
        </p>
        <button
          type="button"
          className="btn-ghost"
          disabled={compareSet.length < 2}
          onClick={() => setCompareOpen(true)}
        >
          Compare
        </button>
      </div>

      <EvidenceDrawer match={inspect} onClose={() => setInspect(null)} />
      <CompareDrawer
        open={compareOpen}
        matches={compareSet}
        peers={matches}
        onClose={() => setCompareOpen(false)}
      />
    </div>
  );
}

function ExpandedMatch({
  match,
  peers,
  compared,
  onInspect,
  onCompare,
  onCollapse,
}: {
  match: RankedProductMatch;
  peers: RankedProductMatch[];
  compared: boolean;
  onInspect: () => void;
  onCompare: () => void;
  onCollapse?: () => void;
}) {
  const reasons = primaryReasons(match, 2);
  const extra = remainingSignalCount(match);
  const overall = matchScoreDisplay(
    match.overall_semantic_fit,
    peers.map((item) => item.overall_semantic_fit),
  );
  const rationale = reasons
    .map((fact) => prettyFactDisplay(fact.attribute, fact.display))
    .join(". ");

  return (
    <article className="border-y border-line py-3">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[15px] font-medium">
          #{match.rank} {match.product_name}
        </p>
        <p className="font-mono text-sm tabular-nums">
          {overall.value}
          <span className="ml-1 text-muted">{overall.suffix}</span>
        </p>
      </div>
      {rationale ? (
        <p className="mt-2 text-sm leading-6 text-muted">{rationale}.</p>
      ) : null}
      {extra > 0 ? (
        <p className="mt-1 text-xs text-muted">
          + {extra} supporting signals available in evidence
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-3">
        <button type="button" className="btn-quiet" onClick={onInspect}>
          Inspect evidence
        </button>
        <button type="button" className="btn-quiet" onClick={onCompare}>
          {compared ? "Selected" : "Compare"}
        </button>
        {onCollapse ? (
          <button type="button" className="btn-quiet" onClick={onCollapse}>
            Collapse
          </button>
        ) : null}
      </div>
    </article>
  );
}

function CompactMatch({
  match,
  peers,
  compared,
  onExpand,
  onCompare,
}: {
  match: RankedProductMatch;
  peers: RankedProductMatch[];
  compared: boolean;
  onExpand: () => void;
  onCompare: () => void;
}) {
  const overall = matchScoreDisplay(
    match.overall_semantic_fit,
    peers.map((item) => item.overall_semantic_fit),
  );
  return (
    <article className="flex flex-wrap items-baseline justify-between gap-3 py-2.5">
      <button
        type="button"
        onClick={onExpand}
        aria-expanded={false}
        className="min-w-0 flex-1 text-left text-[15px] font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        #{match.rank} {match.product_name}
      </button>
      <p className="font-mono text-sm tabular-nums">
        {overall.value}
      </p>
      <button type="button" className="btn-quiet" onClick={onCompare}>
        {compared ? "Selected" : "Compare"}
      </button>
    </article>
  );
}

function titleCase(value: string | null | undefined): string {
  if (!value) return "—";
  return value.charAt(0) + value.slice(1).toLowerCase();
}

function EvidenceDrawer({
  match,
  onClose,
}: {
  match: RankedProductMatch | null;
  onClose: () => void;
}) {
  return (
    <Drawer
      open={Boolean(match)}
      title={match ? `Evidence · ${match.product_name}` : "Evidence"}
      onClose={onClose}
    >
      {match ? (
        <div className="space-y-5">
          {proofItems(match).map((item) => {
            const badge = sourceBadge(item.source_type, item.source_name);
            return (
              <section key={`${item.claim_key}-${String(item.value)}`}>
                <p className="eyebrow">Claim</p>
                <p className="mt-1 text-sm font-medium">{item.display_claim}</p>
                <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                  <dt className="text-muted">Canonical field</dt>
                  <dd className="font-mono">{item.claim_key}</dd>
                  <dt className="text-muted">Value</dt>
                  <dd>
                    {String(item.value)}
                    {item.unit ? ` ${item.unit}` : ""}
                  </dd>
                  <dt className="text-muted">Source</dt>
                  <dd>
                    <EvidenceBadge source={badge} />{" "}
                    {item.source_name ?? item.source_type}
                  </dd>
                  <dt className="text-muted">Source record</dt>
                  <dd className="font-mono">
                    {item.source_record_id ?? "—"}
                  </dd>
                  <dt className="text-muted">Verification</dt>
                  <dd>{titleCase(item.verification_status)}</dd>
                  <dt className="text-muted">Freshness</dt>
                  <dd>{titleCase(item.freshness_status)}</dd>
                  <dt className="text-muted">Observed</dt>
                  <dd>{item.observed_at ?? "—"}</dd>
                  <dt className="text-muted">Derived</dt>
                  <dd>{item.derived ? "Yes" : "No"}</dd>
                  {item.derived && item.derivation_rule ? (
                    <>
                      <dt className="text-muted">Derivation rule</dt>
                      <dd className="font-mono">{item.derivation_rule}</dd>
                    </>
                  ) : null}
                </dl>
              </section>
            );
          })}
          {match.unsupported_needs.length ? (
            <p className="text-sm text-uncertain">
              Limited evidence: {match.unsupported_needs.map(contextLabel).join(", ")}
            </p>
          ) : null}
        </div>
      ) : null}
    </Drawer>
  );
}

function CompareDrawer({
  open,
  matches,
  peers,
  onClose,
}: {
  open: boolean;
  matches: RankedProductMatch[];
  peers: RankedProductMatch[];
  onClose: () => void;
}) {
  const rows = useMemo(
    () => [
      { label: "Price", values: matches.map((item) => formatAudCents(item.base_price_cents)) },
      {
        label: "Overall match",
        values: matches.map((item) => String(Math.round(item.overall_semantic_fit * 100))),
      },
      {
        label: "Product fit",
        values: matches.map((item) => String(Math.round(item.product_fit * 100))),
      },
      {
        label: "Context fit",
        values: matches.map((item) => String(Math.round(item.context_fit * 100))),
      },
      {
        label: "Preference fit",
        values: matches.map((item) => String(Math.round(item.preference_fit * 100))),
      },
      {
        label: "Evidence coverage",
        values: matches.map((item) => {
          const rate = displayedCoverage(item);
          return rate == null ? "—" : `${Math.round(rate * 100)}%`;
        }),
      },
      {
        label: "Battery",
        values: matches.map((item) => factValue(item, ["battery_hours", "battery"]) ?? "—"),
      },
      {
        label: "Weight",
        values: matches.map((item) => factValue(item, ["weight_g", "weight"]) ?? "—"),
      },
      {
        label: "ANC",
        values: matches.map((item) => factValue(item, ["anc"]) ?? "—"),
      },
      {
        label: "Key strength",
        values: matches.map((item) => {
          const fact = primaryReasons(item, 1)[0];
          return fact ? prettyFactDisplay(fact.attribute, fact.display) : "—";
        }),
      },
      {
        label: "Key trade-off",
        values: matches.map((item) => tradeOffLine(item, peers) ?? "—"),
      },
    ],
    [matches, peers],
  );

  return (
    <Drawer open={open} title="Compare matches" onClose={onClose}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[420px] text-left text-xs">
          <thead>
            <tr className="border-b border-line text-muted">
              <th className="py-2 font-medium"> </th>
              {matches.map((item) => (
                <th key={item.variant_id} className="py-2 font-medium">
                  {item.product_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-line">
                <th className="py-2 font-medium text-muted">{row.label}</th>
                {row.values.map((value, index) => (
                  <td key={`${row.label}-${index}`} className="py-2">
                    {value}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Drawer>
  );
}
