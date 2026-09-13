"use client";

import { useEffect, useMemo, useState } from "react";

import { QualificationInspect } from "@/components/live/QualificationInspect";
import {
  StagePrimaryAction,
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import { qualifyIntent } from "@/lib/api";
import { exclusionSummary } from "@/lib/qualifyDisplay";
import type { MatchResponse, QualifyResponse } from "@/types";

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
  const reasons = useMemo(() => exclusionSummary(detail), [detail]);

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
            {reasons.slice(0, 8).map((row) => (
              <div
                key={row.label}
                className="flex items-baseline justify-between gap-6"
              >
                <dt className="min-w-0">{row.label}</dt>
                <dd className="shrink-0 font-mono tabular-nums text-muted">
                  {row.count}
                </dd>
              </div>
            ))}
          </dl>
        </StageSection>
      ) : null}
    </>
  );
}
