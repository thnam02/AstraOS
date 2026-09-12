import { Chip } from "@/components/shared/Chip";
import { contextLabel, fieldLabel } from "@/lib/intent";
import { formatAudCents } from "@/lib/money";
import type { ShoppingIntent } from "@/types";

function importanceLabel(value: number): string {
  if (value >= 0.75) return "High";
  if (value <= 0.25) return "Low";
  return "Medium";
}

function formatConstraint(
  operator: string,
  value: unknown,
  unit: string | null,
): string {
  if (unit === "AUD_CENTS" && typeof value === "number") {
    const symbol = operator === "LT" ? "<" : operator === "LTE" ? "≤" : operator;
    return `${symbol} ${formatAudCents(value)}`;
  }
  if (unit === "DAYS" && value === 0) return "today";
  if (operator === "EQ" && value === true) return "";
  if (operator === "EQ" && value === false) return "must be false";
  return `${operator} ${String(value)}`;
}

export function IntentPanel({ intent }: { intent: ShoppingIntent }) {
  return (
    <div className="space-y-4">
      <section>
        <p className="eyebrow">Mandatory</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {intent.hard_constraints.map((item) => (
            <Chip key={item.id}>
              {fieldLabel(item.field)}{" "}
              {formatConstraint(
                item.operator,
                item.normalized_value ?? item.value,
                item.unit,
              )}
            </Chip>
          ))}
        </div>
      </section>

      {intent.context_items.length ? (
        <section>
          <p className="eyebrow">Context</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {intent.context_items.map((item) => (
              <Chip key={item.label}>{contextLabel(item.label)}</Chip>
            ))}
          </div>
        </section>
      ) : null}

      {intent.soft_preferences.length ? (
        <section>
          <p className="eyebrow">Priorities</p>
          <dl className="mt-2 space-y-1 text-sm">
            {intent.soft_preferences.map((item) => (
              <div key={item.id} className="flex justify-between gap-3">
                <dt>{fieldLabel(item.field)}</dt>
                <dd className="text-muted">{importanceLabel(item.importance)}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}

      {intent.desired_outcomes.length ? (
        <section>
          <p className="eyebrow">Desired outcomes</p>
          <p className="mt-2 text-sm leading-6">
            {intent.desired_outcomes.map((item) => contextLabel(item.label)).join(" · ")}
          </p>
        </section>
      ) : null}

      {intent.tradeoffs.length ? (
        <section>
          <p className="eyebrow">Trade-off</p>
          <div className="mt-2 space-y-2 text-sm">
            {intent.tradeoffs.map((item) => (
              <p key={`${item.preferred_dimension}-${item.over_dimension}`}>
                {fieldLabel(item.preferred_dimension)}
                <span className="mx-2 text-muted">{">"}</span>
                {item.over_dimension === "price"
                  ? "lowest possible price"
                  : fieldLabel(item.over_dimension)}
              </p>
            ))}
          </div>
        </section>
      ) : null}

      {intent.unsupported_semantic_needs.length || intent.ambiguities.length ? (
        <section>
          <p className="eyebrow">Unsupported / clarify</p>
          <div className="mt-2 space-y-1 text-sm text-uncertain">
            {intent.unsupported_semantic_needs.map((item) => (
              <p key={item.label}>{item.source_phrase}</p>
            ))}
            {intent.ambiguities.map((item) => (
              <p key={item.source_phrase}>{item.source_phrase}</p>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
