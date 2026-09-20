"use client";

import { useEffect, useState } from "react";

import { AstraPanel } from "@/components/astra";

import { QualificationInspect } from "@/components/live/QualificationInspect";
import { QualificationResults } from "@/components/live/QualificationResults";
import {
  StagePrimaryAction,
  StageMetricStrip,
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
    <div className="qualification-stage grid gap-3">
      <AstraPanel tone="primary">
        <div className="grid items-center gap-4 lg:grid-cols-2">
          <div>
            <p className="eyebrow text-mark">Qualification summary</p>
            <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <h3 className="text-xl font-semibold tracking-tight">
                {eligible} of {checked} variants remain eligible
              </h3>
              <p className="font-mono text-2xl font-semibold tabular-nums">
                {rate}%
              </p>
            </div>
            <p className="mt-1 text-sm text-muted">
              Semantic ranking runs only on eligible SKUs.
            </p>
          </div>
          <StageMetricStrip
            items={[
              { label: "Eligible", value: eligible },
              { label: "Violated", value: qualification.violated },
              { label: "Unknown", value: qualification.uncertain },
            ]}
          />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <div className="h-2 min-w-24 flex-1 bg-line-muted" aria-hidden>
            <div
              className="h-2 bg-mark"
              style={{ width: `${eligibleWidth}%` }}
            />
          </div>
          <StagePrimaryAction
            label="Continue to product matching"
            onClick={onContinue}
          />
          <QualificationInspect
            intentText={intentText}
            parserMode={parserMode}
          />
        </div>
      </AstraPanel>

      {detail ? (
        <QualificationResults detail={detail} layout="columns" />
      ) : (
        <AstraPanel>
          <p className="eyebrow">Qualification results</p>
          <p className="mt-2 text-sm text-muted">
            {detailError
              ? "Eligibility detail is unavailable for this run."
              : "Loading eligibility detail…"}
          </p>
        </AstraPanel>
      )}
    </div>
  );
}
