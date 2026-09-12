"use client";

import { useMemo, useState } from "react";

import { Drawer } from "@/components/shared/Drawer";
import { EvidenceBadge } from "@/components/shared/EvidenceBadge";
import { ScoreBar } from "@/components/shared/ScoreBar";
import { contextLabel } from "@/lib/intent";
import { matchScoreDisplay, strengthHint } from "@/lib/decisionNarrative";
import {
  displayedCoverage,
  factValue,
  groupedRationale,
  prettyFactDisplay,
  primaryReasons,
  proofItems,
  remainingSignalCount,
  sourceBadge,
  tradeOffLine,
} from "@/lib/matchDisplay";
import { formatAudCents } from "@/lib/money";
import type { RankedProductMatch } from "@/types";

export function MatchList({ matches }: { matches: RankedProductMatch[] }) {
  const [expanded, setExpanded] = useState<string | null>(
    matches[0]?.variant_id ?? null,
  );
  const [inspect, setInspect] = useState<RankedProductMatch | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);

  const compareSet = matches.filter((item) => compareIds.includes(item.variant_id));

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
    <div className="space-y-3">
      {matches.slice(0, 5).map((match, index) => {
        const open = match.variant_id === expanded || index === 0;
        if (index === 0 || open) {
          return (
            <ExpandedMatch
              key={match.variant_id}
              match={match}
              peers={matches}
              compared={compareIds.includes(match.variant_id)}
              onInspect={() => setInspect(match)}
              onCompare={() => toggleCompare(match.variant_id)}
              onCollapse={
                index === 0 ? undefined : () => setExpanded(matches[0]?.variant_id ?? null)
              }
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

      {matches.length > 5 ? (
        <p className="text-xs text-muted">+ {matches.length - 5} additional matches</p>
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
  const reasons = primaryReasons(match, 4);
  const groups = groupedRationale(match);
  const extra = remainingSignalCount(match);
  const trade = tradeOffLine(match, peers);
  const bestFor = groups.slice(0, 2).map((item) => item.label);
  const overall = matchScoreDisplay(
    match.overall_semantic_fit,
    peers.map((item) => item.overall_semantic_fit),
  );

  return (
    <article className="bg-canvas px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Top product match</p>
          <p className="mt-1 text-[22px] font-semibold tracking-tight">
            #{match.rank} {match.product_name}
          </p>
          <p className="font-mono text-[11px] text-muted">{match.sku}</p>
        </div>
        <div className="text-right">
          <p className="text-[11px] text-success">PASS</p>
          <p className="font-mono text-sm tabular-nums">
            {formatAudCents(match.base_price_cents)}
          </p>
        </div>
      </div>

      <div className="mt-3">
        <p className="eyebrow" title="How strongly the product itself aligns with buyer context and preferences.">
          Overall product match
        </p>
        <ScoreBar
          value={match.overall_semantic_fit}
          large
          display={overall.value}
          suffix={overall.suffix}
        />
      </div>

      <dl className="mt-3 grid gap-2 sm:grid-cols-3">
        <div>
          <ScoreBar label="Product fit" value={match.product_fit} />
        </div>
        <div>
          <ScoreBar label="Context fit" value={match.context_fit} />
        </div>
        <div>
          <ScoreBar label="Preference fit" value={match.preference_fit} />
        </div>
      </dl>

      {bestFor.length ? (
        <p className="mt-3 text-sm">
          <span className="text-xs text-muted">Best for </span>
          {bestFor.join(" · ")}
        </p>
      ) : null}

      <div className="mt-3">
        <p className="eyebrow">Key strengths</p>
        <ul className="mt-2 space-y-1.5 text-sm">
          {reasons.map((fact) => (
            <li key={`${fact.attribute}-${fact.display}`}>
              <span>{prettyFactDisplay(fact.attribute, fact.display)}</span>{" "}
              <EvidenceBadge
                source={sourceBadge(fact.source_type, fact.source_name)}
              />
              {strengthHint(fact.attribute) ? (
                <span className="ml-2 text-xs text-muted">
                  {strengthHint(fact.attribute)}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
        {extra > 0 ? (
          <p className="mt-1 text-xs text-muted">+ {extra} more supporting signals</p>
        ) : null}
      </div>

      <p
        className="mt-3 text-xs text-muted"
        title="Share of displayed match reasons with evidence or a documented derivation. Separate from Product / Context / Preference Fit."
      >
        Evidence coverage{" "}
        {displayedCoverage(match) == null
          ? "—"
          : `${Math.round((displayedCoverage(match) ?? 0) * 100)}%`}
        {trade ? ` · ${trade}` : ""}
      </p>

      <div className="mt-2 flex flex-wrap gap-3">
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
    <article className="flex flex-wrap items-center justify-between gap-3 py-2">
      <div>
        <p className="text-sm font-medium">
          #{match.rank} {match.product_name}{" "}
          <span className="font-mono text-muted">
            {overall.value} {overall.suffix}
          </span>
        </p>
        <p className="text-xs text-muted">
          Context {Math.round(match.context_fit * 100)} · Preference{" "}
          {Math.round(match.preference_fit * 100)} · Evidence{" "}
          {displayedCoverage(match) == null
            ? "—"
            : Math.round((displayedCoverage(match) ?? 0) * 100)}
        </p>
      </div>
      <div className="flex gap-3">
        <button type="button" className="btn-quiet" onClick={onExpand}>
          Expand
        </button>
        <button type="button" className="btn-quiet" onClick={onCompare}>
          {compared ? "Selected" : "Compare"}
        </button>
      </div>
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
