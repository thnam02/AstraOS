"use client";

import { useEffect, useMemo, useState } from "react";

import { QualificationInspect } from "@/components/live/QualificationInspect";
import {
  StagePrimaryAction,
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import { qualifyIntent } from "@/lib/api";
import type { MatchResponse, QualifyResponse } from "@/types";

function exclusionCounts(detail: QualifyResponse | null) {
  if (!detail) return [];
  const counts = new Map<string, number>();
  for (const item of detail.rejected_products) {
    const reasons = item.exclusion_reasons.length
      ? item.exclusion_reasons
      : ["Unspecified constraint"];
    for (const reason of reasons) {
      counts.set(reason, (counts.get(reason) ?? 0) + 1);
    }
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

export function QualifyStage({
  qualification,
  intentText,
  parserMode,
  onContinue,
}: {
  qualification: MatchResponse["qualification"];
  intentText: string;
  parserMode: "rule_based" | "llm";
  onContinue?: () => void;
}) {
  const [detail, setDetail] = useState<QualifyResponse | null>(null);
  const checked = qualification.variants_checked;
  const eligible = qualification.eligible;
  const rate = checked ? Math.round((eligible / checked) * 1000) / 10 : 0;
  const eligibleWidth = checked ? Math.max(4, (eligible / checked) * 100) : 0;
  const reasons = useMemo(() => exclusionCounts(detail), [detail]);

  useEffect(() => {
    let cancelled = false;
    qualifyIntent(intentText, parserMode)
      .then((payload) => {
        if (!cancelled) setDetail(payload);
      })
      .catch(() => {
        if (!cancelled) setDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [intentText, parserMode]);

  return (
    <>
      <StageResult
        label="Qualification result"
        title={`${eligible} of ${checked} variants remain eligible`}
        value={`${rate}%`}
        explanation={
          <p className="text-muted">
            Semantic ranking runs only on eligible SKUs.
          </p>
        }
        metrics={[
          { label: "Eligible", value: eligible },
          { label: "Rejected", value: qualification.violated },
          { label: "Unknown", value: qualification.uncertain },
        ]}
        actions={
          <>
            <StagePrimaryAction
              label="Continue to product matching"
              onClick={onContinue}
            />
            <QualificationInspect intentText={intentText} parserMode={parserMode} />
          </>
        }
      >
        <div className="h-2 bg-line-muted" aria-hidden>
          <div className="h-2 bg-mark" style={{ width: `${eligibleWidth}%` }} />
        </div>
      </StageResult>

      {reasons.length ? (
        <StageSection title="Why variants were excluded">
          <dl className="max-w-lg space-y-2 text-sm">
            {reasons.slice(0, 8).map(([reason, count]) => (
              <div key={reason} className="flex justify-between gap-4">
                <dt>{reason}</dt>
                <dd className="font-mono tabular-nums">{count}</dd>
              </div>
            ))}
          </dl>
        </StageSection>
      ) : null}
    </>
  );
}
