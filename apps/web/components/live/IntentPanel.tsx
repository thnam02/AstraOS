import { useState } from "react";

import {
  constraintLabel,
  contextLabel,
  fieldLabel,
  importanceLabel,
} from "@/lib/intent";
import type { ShoppingIntent } from "@/types";

function QuotedChip({
  label,
  source,
  onSelect,
}: {
  label: string;
  source?: string;
  onSelect: (source: string) => void;
}) {
  return (
    <button
      type="button"
      className="chip-soft text-left"
      onClick={() => source && onSelect(source)}
    >
      {label}
    </button>
  );
}

export function IntentPanel({
  intent,
  compact = false,
}: {
  intent: ShoppingIntent;
  compact?: boolean;
}) {
  const [quote, setQuote] = useState<string | null>(null);
  const meta = intent.parser_metadata;
  const parserName = meta?.parser_used ?? intent.parser_type;

  return (
    <div className="space-y-4">
      {compact ? null : (
      <section className="flex flex-wrap gap-4 text-xs">
        <div>
          <p className="eyebrow">Parser</p>
          <p className="mt-1 font-medium uppercase tracking-wide">
            {parserName === "llm" ? "LLM" : "Rule-based"}
          </p>
        </div>
        <div>
          <p className="eyebrow">Fallback</p>
          <p className="mt-1 font-medium">{meta?.fallback_used ? "Yes" : "No"}</p>
        </div>
      </section>
      )}

      <section>
        <p className="eyebrow">Mandatory</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {intent.hard_constraints.map((item) => (
            <QuotedChip
              key={item.id}
              label={constraintLabel(item)}
              source={item.source_phrase}
              onSelect={setQuote}
            />
          ))}
        </div>
      </section>

      {intent.context_items.length ? (
        <section>
          <p className="eyebrow">Context</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {intent.context_items.map((item) => (
              <QuotedChip
                key={item.label}
                label={contextLabel(item.label)}
                source={item.source_phrase}
                onSelect={setQuote}
              />
            ))}
          </div>
        </section>
      ) : null}

      {intent.soft_preferences.length ? (
        <section>
          <p className="eyebrow">Priorities</p>
          <dl className="mt-2 space-y-1 text-sm">
            {intent.soft_preferences.map((item) => (
              <button
                key={item.id}
                type="button"
                className="flex w-full justify-between gap-3 text-left"
                onClick={() => setQuote(item.source_phrase)}
              >
                <dt>{fieldLabel(item.field)}</dt>
                <dd className="text-muted">{importanceLabel(item.importance)}</dd>
              </button>
            ))}
          </dl>
        </section>
      ) : null}

      {intent.desired_outcomes.length ? (
        <section>
          <p className="eyebrow">Desired outcomes</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {intent.desired_outcomes.map((item) => (
              <QuotedChip
                key={item.label}
                label={contextLabel(item.label)}
                source={item.source_phrase}
                onSelect={setQuote}
              />
            ))}
          </div>
        </section>
      ) : null}

      {compact ? null : intent.values.length ? (
        <section>
          <p className="eyebrow">Values</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {intent.values.map((item) => (
              <QuotedChip
                key={item.field}
                label={fieldLabel(item.field)}
                source={item.source_phrase}
                onSelect={setQuote}
              />
            ))}
          </div>
        </section>
      ) : null}

      {intent.tradeoffs.length ? (
        <section>
          <p className="eyebrow">Trade-offs</p>
          <div className="mt-2 space-y-2 text-sm">
            {intent.tradeoffs.map((item) => (
              <button
                key={`${item.preferred_dimension}-${item.over_dimension}`}
                type="button"
                className="block text-left"
                onClick={() => setQuote(item.source_phrase)}
              >
                {fieldLabel(item.preferred_dimension)}
                <span className="mx-2 text-muted">{">"}</span>
                {item.over_dimension === "price"
                  ? "lowest possible price"
                  : fieldLabel(item.over_dimension)}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {intent.ambiguities.length ? (
        <section>
          <p className="eyebrow">Ambiguities</p>
          <div className="mt-2 space-y-1 text-sm text-uncertain">
            {intent.ambiguities.map((item) => (
              <button
                key={`${item.reason}-${item.source_phrase}`}
                type="button"
                className="block text-left"
                onClick={() => setQuote(item.source_phrase)}
              >
                {item.source_phrase}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {intent.unsupported_semantic_needs.length ? (
        <section>
          <p className="eyebrow">Unsupported needs</p>
          <div className="mt-2 space-y-1 text-sm text-uncertain">
            {intent.unsupported_semantic_needs.map((item) => (
              <button
                key={item.label}
                type="button"
                className="block text-left"
                onClick={() => setQuote(item.source_phrase)}
              >
                {item.source_phrase}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {quote ? (
        <p className="rounded-md border border-line bg-surface px-3 py-2 text-xs leading-5 text-muted">
          Buyer text: “{quote}”
        </p>
      ) : (
        <p className="text-[11px] text-muted">
          Click an extracted item to see the buyer phrase it came from.
        </p>
      )}
    </div>
  );
}