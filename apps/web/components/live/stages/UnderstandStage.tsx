"use client";

import type { ReactNode } from "react";

import {
  StageDisclosure,
  StagePrimaryAction,
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import {
  constraintLabel,
  contextLabel,
  fieldLabel,
  importanceLabel,
  intentNarrative,
} from "@/lib/intent";
import type { ShoppingIntent } from "@/types";

export function UnderstandStage({
  intent,
  rawText,
  onInspect,
  onContinue,
}: {
  intent: ShoppingIntent;
  rawText: string;
  onInspect: () => void;
  onContinue?: () => void;
}) {
  const hasNotes =
    intent.tradeoffs.length > 0 ||
    intent.ambiguities.length > 0 ||
    intent.unsupported_semantic_needs.length > 0;

  return (
    <>
      <StageSection title="Buyer request">
        <p className="max-w-2xl text-[15px] leading-6">“{rawText}”</p>
      </StageSection>

      <StageResult
        label="Interpreted intent"
        explanation={<p>{intentNarrative(intent)}</p>}
        actions={
          <>
            <StagePrimaryAction
              label="Continue to qualification"
              onClick={onContinue}
            />
            <button type="button" className="btn-quiet" onClick={onInspect}>
              Inspect extraction
            </button>
          </>
        }
      >
        <div className="grid gap-6 sm:grid-cols-2">
          <IntentCluster title="Mandatory">
            {intent.hard_constraints.length ? (
              <ul className="space-y-1.5 text-sm">
                {intent.hard_constraints.map((item) => (
                  <li key={item.id}>{constraintLabel(item)}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">None extracted.</p>
            )}
          </IntentCluster>
          <IntentCluster title="Context">
            {intent.context_items.length ? (
              <ul className="space-y-1.5 text-sm">
                {intent.context_items.map((item) => (
                  <li key={item.label}>{contextLabel(item.label)}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">None extracted.</p>
            )}
          </IntentCluster>
          <IntentCluster title="Priorities">
            {intent.soft_preferences.length ? (
              <dl className="space-y-1.5 text-sm">
                {intent.soft_preferences.map((item) => (
                  <div key={item.id} className="flex justify-between gap-4">
                    <dt>{fieldLabel(item.field)}</dt>
                    <dd className="text-muted">{importanceLabel(item.importance)}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-sm text-muted">None extracted.</p>
            )}
          </IntentCluster>
          <IntentCluster title="Desired outcomes">
            {intent.desired_outcomes.length ? (
              <ul className="space-y-1.5 text-sm">
                {intent.desired_outcomes.map((item) => (
                  <li key={item.label}>{contextLabel(item.label)}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">None extracted.</p>
            )}
          </IntentCluster>
        </div>
      </StageResult>

      {hasNotes ? (
        <StageSection title="Interpretation notes">
          <div className="grid gap-6 sm:grid-cols-3">
            {intent.tradeoffs.length ? (
              <IntentCluster title="Trade-offs">
                <ul className="space-y-1.5 text-sm">
                  {intent.tradeoffs.map((item) => (
                    <li key={`${item.preferred_dimension}-${item.over_dimension}`}>
                      {fieldLabel(item.preferred_dimension)}
                      <span className="mx-2 text-muted">{">"}</span>
                      {item.over_dimension === "price"
                        ? "lowest possible price"
                        : fieldLabel(item.over_dimension)}
                    </li>
                  ))}
                </ul>
              </IntentCluster>
            ) : null}
            {intent.ambiguities.length ? (
              <IntentCluster title="Ambiguities">
                <ul className="space-y-1.5 text-sm text-uncertain">
                  {intent.ambiguities.map((item) => (
                    <li key={`${item.reason}-${item.source_phrase}`}>
                      {item.source_phrase}
                    </li>
                  ))}
                </ul>
              </IntentCluster>
            ) : null}
            {intent.unsupported_semantic_needs.length ? (
              <IntentCluster title="Unsupported needs">
                <ul className="space-y-1.5 text-sm text-uncertain">
                  {intent.unsupported_semantic_needs.map((item) => (
                    <li key={item.label}>{item.source_phrase}</li>
                  ))}
                </ul>
              </IntentCluster>
            ) : null}
          </div>
        </StageSection>
      ) : null}

      <StageDisclosure title="Parsing details">
        <dl className="grid max-w-md grid-cols-2 gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted">Parser</dt>
          <dd>
            {(intent.parser_metadata?.parser_used ?? intent.parser_type) === "llm"
              ? "LLM"
              : "Rule-based"}
          </dd>
          <dt className="text-muted">Fallback</dt>
          <dd>{intent.parser_metadata?.fallback_used ? "Yes" : "No"}</dd>
          {intent.parser_metadata?.fallback_reason ? (
            <>
              <dt className="text-muted">Reason</dt>
              <dd>{intent.parser_metadata.fallback_reason}</dd>
            </>
          ) : null}
        </dl>
      </StageDisclosure>
    </>
  );
}

function IntentCluster({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div>
      <p className="type-small text-muted">{title}</p>
      <div className="mt-2">{children}</div>
    </div>
  );
}
