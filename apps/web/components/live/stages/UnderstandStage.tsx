"use client";

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
  return (
    <>
      <StageResult
        label="Interpreted buyer request"
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
      />

      {intent.hard_constraints.length ? (
        <StageSection title="Mandatory requirements">
          <ul className="space-y-2 text-[15px]">
            {intent.hard_constraints.map((item) => (
              <li key={item.id}>{constraintLabel(item)}</li>
            ))}
          </ul>
        </StageSection>
      ) : null}

      {intent.soft_preferences.length ? (
        <StageSection title="Preferences">
          <dl className="max-w-md space-y-2 text-[15px]">
            {intent.soft_preferences.map((item) => (
              <div key={item.id} className="flex justify-between gap-6">
                <dt>{fieldLabel(item.field)}</dt>
                <dd className="text-muted">{importanceLabel(item.importance)}</dd>
              </div>
            ))}
          </dl>
        </StageSection>
      ) : null}

      {intent.context_items.length ? (
        <StageSection title="Context">
          <ul className="space-y-2 text-[15px]">
            {intent.context_items.map((item) => (
              <li key={item.label}>{contextLabel(item.label)}</li>
            ))}
          </ul>
        </StageSection>
      ) : null}

      {intent.desired_outcomes.length ? (
        <StageSection title="Desired outcomes">
          <ul className="space-y-2 text-[15px]">
            {intent.desired_outcomes.map((item) => (
              <li key={item.label}>{contextLabel(item.label)}</li>
            ))}
          </ul>
        </StageSection>
      ) : null}

      {intent.tradeoffs.length ? (
        <StageSection title="Trade-offs">
          <ul className="space-y-2 text-[15px]">
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
        </StageSection>
      ) : null}

      <div className="flex flex-wrap gap-4">
        <StageDisclosure title="View original request">
          <p className="max-w-2xl text-sm leading-6 text-muted">“{rawText}”</p>
        </StageDisclosure>
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
      </div>
    </>
  );
}
