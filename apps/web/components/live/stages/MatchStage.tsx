"use client";

import { useState } from "react";

import { MatchList } from "@/components/live/MatchList";
import {
  StagePrimaryAction,
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import { matchScoreDisplay } from "@/lib/decisionNarrative";
import {
  groupedRationale,
  primaryReasons,
  prettyFactDisplay,
} from "@/lib/matchDisplay";
import type { RankedProductMatch } from "@/types";

export function MatchStage({
  matches,
  onContinue,
}: {
  matches: RankedProductMatch[];
  onContinue?: () => void;
}) {
  const [inspectNonce, setInspectNonce] = useState(0);
  const [compareNonce, setCompareNonce] = useState(0);
  const top = matches[0] ?? null;
  if (!top) {
    return <p className="text-sm text-muted">No eligible products to rank.</p>;
  }
  const overall = matchScoreDisplay(
    top.overall_semantic_fit,
    matches.map((item) => item.overall_semantic_fit),
  );
  const groups = groupedRationale(top, 2);
  const reasons = primaryReasons(top, 2);
  const explanation = groups.length
    ? `Strong fit for ${groups.map((item) => item.label.toLowerCase()).join(" and ")}.`
    : reasons.length
      ? reasons
          .map((fact) => prettyFactDisplay(fact.attribute, fact.display))
          .join(". ") + "."
      : null;

  return (
    <div className="grid gap-3">
      <StageResult
        label="Best product match"
        title={top.product_name}
        value={
          <>
            {overall.value}
            <span className="ml-1 text-sm font-medium text-muted">
              {overall.suffix}
            </span>
          </>
        }
        explanation={explanation ? <p>{explanation}</p> : undefined}
        metrics={[
          { label: "Product fit", value: Math.round(top.product_fit * 100) },
          { label: "Context fit", value: Math.round(top.context_fit * 100) },
          {
            label: "Preference fit",
            value: Math.round(top.preference_fit * 100),
          },
        ]}
        actions={
          <>
            <StagePrimaryAction
              label="Continue to offer construction"
              onClick={onContinue}
            />
            <button
              type="button"
              className="btn-quiet"
              onClick={() => setInspectNonce((current) => current + 1)}
            >
              Inspect evidence
            </button>
            <button
              type="button"
              className="btn-quiet"
              onClick={() => setCompareNonce((current) => current + 1)}
            >
              Compare products
            </button>
          </>
        }
      />

      <StageSection
        title="Other matches"
        description="Compact ranked list. Evidence stays in the inspector."
      >
        <MatchList
          matches={matches}
          inspectNonce={inspectNonce}
          compareNonce={compareNonce}
        />
      </StageSection>
    </div>
  );
}
