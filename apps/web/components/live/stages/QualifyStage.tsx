"use client";

import { useEffect, useState } from "react";

import { QualificationInspect } from "@/components/live/QualificationInspect";
import { QualificationResults } from "@/components/live/QualificationResults";
import {
  StagePrimaryAction,
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import { qualifyIntent } from "@/lib/api";
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
  const [detailError, setDetailError] = useState(false);
  const checked = qualification.variants_checked;
  const eligible = qualification.eligible;
  const rate = checked ? Math.round((eligible / checked) * 1000) / 10 : 0;
  const eligibleWidth = checked ? Math.max(4, (eligible / checked) * 100) : 0;

  useEffect(() => {
    let cancelled = false;
    qualifyIntent(intentText, parserMode)
      .then((payload) => {
        if (!cancelled) {
          setDetail(payload);
          setDetailError(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDetail(null);
          setDetailError(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [intentText, parserMode]);

  return (
    <>
      <StageResult
        label="Qualification summary"
        title={`${eligible} of ${checked} variants remain eligible`}
        value={`${rate}%`}
        explanation={
          <p className="text-muted">
            Semantic ranking runs only on eligible SKUs.
          </p>
        }
        metrics={[
          { label: "Eligible", value: eligible },
          { label: "Violated", value: qualification.violated },
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

      <StageSection title="Qualification results">
        {detail ? (
          <QualificationResults detail={detail} />
        ) : detailError ? (
          <p className="text-sm text-muted">
            Eligibility detail is unavailable for this run.
          </p>
        ) : (
          <p className="text-sm text-muted">Loading eligibility detail…</p>
        )}
      </StageSection>
    </>
  );
}
