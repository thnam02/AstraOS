"use client";

import { useMemo, useState } from "react";

import { ApiStatus } from "@/components/live/ApiStatus";
import { qualifyIntent } from "@/lib/api";
import { HERO_INTENT, contextLabel, fieldLabel } from "@/lib/intent";
import { formatAudCents } from "@/lib/money";
import type {
  ConstraintEvaluation,
  ConstraintStatus,
  QualifyResponse,
  VariantQualificationCard,
} from "@/types";

type Filter = "eligible" | "uncertain" | "rejected";

const PROCESS = [
  { id: "understand", label: "Understand", after: "complete" },
  { id: "qualify", label: "Qualify", after: "complete" },
  { id: "construct", label: "Construct", after: "not_started" },
  { id: "optimise", label: "Optimise", after: "not_started" },
  { id: "prove", label: "Prove", after: "partial" },
  { id: "learn", label: "Learn", after: "not_started" },
] as const;

export function LiveWorkbench() {
  const [text, setText] = useState(HERO_INTENT);
  const [parserMode, setParserMode] = useState<"rule_based" | "llm">("rule_based");
  const [result, setResult] = useState<QualifyResponse | null>(null);
  const [filter, setFilter] = useState<Filter>("eligible");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [proof, setProof] = useState<{
    product: string;
    evaluation: ConstraintEvaluation;
  } | null>(null);

  async function qualify() {
    setBusy(true);
    setError(null);
    try {
      const payload = await qualifyIntent(text, parserMode);
      setResult(payload);
      if (payload.summary.eligible > 0) setFilter("eligible");
      else if (payload.summary.uncertain > 0) setFilter("uncertain");
      else setFilter("rejected");
    } catch {
      setError("Qualification failed. Is the API running?");
    } finally {
      setBusy(false);
    }
  }

  const cards = useMemo(() => {
    if (!result) return [];
    if (filter === "eligible") return result.eligible_products;
    if (filter === "uncertain") return result.uncertain_products;
    return result.rejected_products;
  }, [filter, result]);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(260px,1fr)_minmax(420px,1.4fr)_minmax(240px,0.9fr)]">
      <section className="space-y-5">
        <div className="space-y-2">
          <p className="text-[11px] font-medium tracking-[0.14em] text-muted">
            AI SHOPPER REQUEST
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            Intent intake
          </h1>
          <p className="text-sm leading-6 text-muted">
            Language is interpreted. Products are not searched — they are
            admitted or excluded by mandatory conditions.
          </p>
        </div>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={10}
          className="w-full resize-y rounded-[6px] border border-line bg-surface px-3 py-3 text-sm leading-6 text-ink outline-none focus:border-ink"
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setText(HERO_INTENT)}
            className="text-xs font-medium tracking-[0.08em] text-muted hover:text-ink"
          >
            Example request
          </button>
          <span className="text-xs text-muted">
            Parser: {parserMode === "rule_based" ? "Rule-based" : "LLM"}
          </span>
          <select
            value={parserMode}
            onChange={(event) =>
              setParserMode(event.target.value as "rule_based" | "llm")
            }
            className="rounded-[6px] border border-line bg-surface px-2 py-1 text-xs text-ink"
          >
            <option value="rule_based">Rule-based</option>
            <option value="llm">LLM</option>
          </select>
        </div>
        <button
          type="button"
          onClick={() => void qualify()}
          disabled={busy || !text.trim()}
          className="rounded-[6px] bg-ink px-4 py-2 text-xs font-medium tracking-[0.12em] text-surface disabled:opacity-40"
        >
          {busy ? "QUALIFYING…" : "QUALIFY REQUEST"}
        </button>
        {error ? <p className="text-sm text-danger">{error}</p> : null}
        <ApiStatus />
      </section>

      <section className="space-y-6">
        <div>
          <p className="text-[11px] font-medium tracking-[0.14em] text-muted">
            QUALIFICATION
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            Condition inspection
          </h2>
        </div>
        {!result ? (
          <p className="text-sm leading-6 text-muted">
            Submit a request to see structured intent and whether each SKU is
            allowed to compete.
          </p>
        ) : (
          <>
            <StructuredIntent intent={result.intent} />
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ["eligible", result.summary.eligible],
                  ["uncertain", result.summary.uncertain],
                  ["rejected", result.summary.violated],
                ] as const
              ).map(([key, count]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFilter(key)}
                  className={`rounded-[6px] border px-2.5 py-1 text-xs capitalize ${
                    filter === key
                      ? "border-ink text-ink"
                      : "border-line text-muted"
                  }`}
                >
                  {key} {count}
                </button>
              ))}
            </div>
            <div className="space-y-3">
              {cards.map((card) => (
                <QualificationRow
                  key={card.variant_id}
                  card={card}
                  onInspect={(evaluation) =>
                    setProof({
                      product: card.product_name,
                      evaluation,
                    })
                  }
                />
              ))}
              {cards.length === 0 ? (
                <p className="text-sm text-muted">No variants in this bucket.</p>
              ) : null}
            </div>
          </>
        )}
      </section>

      <aside className="space-y-6">
        <div>
          <p className="text-[11px] font-medium tracking-[0.14em] text-muted">
            SUMMARY
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            Pipeline
          </h2>
        </div>
        {result ? (
          <div className="space-y-3 text-sm">
            <p className="tabular-nums text-ink">
              {result.summary.variants_checked} variants checked
            </p>
            <p className="text-success">{result.summary.eligible} eligible</p>
            <p className="text-danger">{result.summary.violated} violated</p>
            <p className="text-uncertain">{result.summary.uncertain} uncertain</p>
            <p className="text-xs text-muted">
              {result.timing.total_ms.toFixed(0)} ms total · parse{" "}
              {result.timing.parse_ms.toFixed(0)} ms · eligibility{" "}
              {result.timing.eligibility_ms.toFixed(0)} ms
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted">No run yet.</p>
        )}
        <ol className="space-y-2">
          {PROCESS.map((step) => {
            const state = result ? step.after : "not_started";
            return (
              <li
                key={step.id}
                className="flex items-center justify-between border-b border-line py-2 text-sm"
              >
                <span className="tracking-[0.08em] uppercase text-ink">
                  {step.label}
                </span>
                <span className="text-[11px] tracking-[0.08em] text-muted">
                  {state.replace(/_/g, " ")}
                </span>
              </li>
            );
          })}
        </ol>
        <p className="text-xs leading-5 text-muted">
          Later stages construct offers, optimise, and learn. This view only
          decides who is allowed to compete.
        </p>
      </aside>

      {proof ? (
        <ProofDrawer
          product={proof.product}
          evaluation={proof.evaluation}
          onClose={() => setProof(null)}
        />
      ) : null}
    </div>
  );
}

function StructuredIntent({
  intent,
}: {
  intent: QualifyResponse["intent"];
}) {
  return (
    <div className="space-y-4 border border-line bg-surface px-4 py-4">
      <div>
        <p className="text-[11px] tracking-[0.14em] text-muted">CATEGORY</p>
        <p className="mt-1 text-sm text-ink">{intent.category ?? "Unspecified"}</p>
      </div>
      <div>
        <p className="text-[11px] tracking-[0.14em] text-muted">MANDATORY</p>
        <ul className="mt-2 space-y-1">
          {intent.hard_constraints.map((item) => (
            <li key={item.id} className="text-sm text-ink">
              ✓ {fieldLabel(item.field)} {formatConstraint(item.operator, item.normalized_value ?? item.value, item.unit)}
            </li>
          ))}
        </ul>
      </div>
      {intent.soft_preferences.length ? (
        <div>
          <p className="text-[11px] tracking-[0.14em] text-muted">PREFERENCES</p>
          <ul className="mt-2 space-y-1">
            {intent.soft_preferences.map((item) => (
              <li key={item.id} className="text-sm text-ink">
                {item.direction === "MAXIMIZE" ? "↑" : "↓"} {fieldLabel(item.field)}
                <span className="text-muted">
                  {" "}
                  · {item.direction === "MINIMIZE" && item.field === "price" ? "price sensitivity" : item.direction.toLowerCase()}{" "}
                  {item.importance < 0.4 ? "medium-low" : item.importance > 0.8 ? "high" : "medium"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {intent.context_tags.length ? (
        <div>
          <p className="text-[11px] tracking-[0.14em] text-muted">CONTEXT</p>
          <p className="mt-1 text-sm capitalize text-ink">
            {intent.context_tags.map(contextLabel).join(", ")}
          </p>
        </div>
      ) : null}
      {intent.ambiguities.length ? (
        <div>
          <p className="text-[11px] tracking-[0.14em] text-uncertain">
            NEEDS CLARIFICATION
          </p>
          <ul className="mt-2 space-y-1">
            {intent.ambiguities.map((item) => (
              <li key={item.source_phrase} className="text-sm text-ink">
                “{item.source_phrase}”{" "}
                <span className="text-muted">{item.reason.replace(/_/g, " ")}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function QualificationRow({
  card,
  onInspect,
}: {
  card: VariantQualificationCard;
  onInspect: (evaluation: ConstraintEvaluation) => void;
}) {
  return (
    <article className="border border-line bg-surface px-4 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-sm font-medium tracking-[0.06em] uppercase text-ink">
            {card.product_name}
          </p>
          <p className="font-mono text-[11px] text-muted">
            {card.sku} · {formatAudCents(card.base_price_cents)}
          </p>
        </div>
        <OutcomeMark outcome={card.outcome} />
      </div>
      <dl className="mt-3 space-y-1.5">
        {card.evaluations.map((evaluation) => (
          <button
            key={evaluation.constraint_id}
            type="button"
            onClick={() => onInspect(evaluation)}
            className="flex w-full items-center justify-between gap-3 text-left text-sm"
          >
            <dt className="text-muted">{fieldLabel(evaluation.field)}</dt>
            <dd>
              <StatusMark status={evaluation.status} />
            </dd>
          </button>
        ))}
      </dl>
    </article>
  );
}

function OutcomeMark({ outcome }: { outcome: VariantQualificationCard["outcome"] }) {
  const label =
    outcome === "eligible"
      ? "ELIGIBLE"
      : outcome === "uncertain"
        ? "NOT ELIGIBLE"
        : "REJECTED";
  const tone =
    outcome === "eligible"
      ? "text-success"
      : outcome === "uncertain"
        ? "text-uncertain"
        : "text-danger";
  return <span className={`text-[11px] font-medium tracking-[0.12em] ${tone}`}>{label}</span>;
}

function StatusMark({ status }: { status: ConstraintStatus }) {
  const styles: Record<ConstraintStatus, string> = {
    SATISFIED: "text-success",
    VIOLATED: "text-danger",
    UNKNOWN: "text-uncertain",
  };
  return (
    <span className={`text-[11px] font-medium tracking-[0.1em] ${styles[status]}`}>
      {status}
    </span>
  );
}

function ProofDrawer({
  product,
  evaluation,
  onClose,
}: {
  product: string;
  evaluation: ConstraintEvaluation;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-ink/20">
      <button type="button" className="h-full flex-1" onClick={onClose} aria-label="Close proof" />
      <aside className="h-full w-full max-w-md space-y-5 overflow-y-auto border-l border-line bg-surface px-6 py-8">
        <p className="text-[11px] tracking-[0.14em] text-muted">PROOF</p>
        <div>
          <h3 className="text-xl font-semibold text-ink">{fieldLabel(evaluation.field)}</h3>
          <p className="text-sm text-muted">{product}</p>
        </div>
        <ProofRow label="Status" value={evaluation.status} />
        <ProofRow label="Expected" value={formatValue(evaluation.expected_value)} />
        <ProofRow label="Observed" value={formatValue(evaluation.observed_value)} />
        <ProofRow label="Source" value={evaluation.source_name ?? "Unavailable"} />
        <ProofRow
          label="Verification"
          value={evaluation.verification_status ?? "Not attached"}
        />
        <ProofRow
          label="Freshness"
          value={evaluation.evidence_freshness ?? "MISSING"}
        />
        <ProofRow
          label="Observed at"
          value={evaluation.observed_at ? evaluation.observed_at.slice(0, 10) : "—"}
        />
        {evaluation.supporting_detail ? (
          <ProofRow label="Delivery option" value={evaluation.supporting_detail} />
        ) : null}
        <p className="text-xs leading-5 text-muted">{evaluation.reason.replace(/_/g, " ")}</p>
        <button
          type="button"
          onClick={onClose}
          className="text-xs tracking-[0.12em] text-muted hover:text-ink"
        >
          CLOSE
        </button>
      </aside>
    </div>
  );
}

function ProofRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] tracking-[0.12em] text-muted">{label.toUpperCase()}</p>
      <p className="mt-1 text-sm text-ink">{value}</p>
    </div>
  );
}

function formatConstraint(operator: string, value: unknown, unit: string | null): string {
  if (unit === "AUD_CENTS" && typeof value === "number") {
    const symbol = operator === "LT" ? "<" : operator === "LTE" ? "≤" : operator;
    return `${symbol} ${formatAudCents(value)}`;
  }
  if (unit === "DAYS" && value === 0) return "today";
  if (operator === "EQ" && value === true) return "required";
  if (operator === "EQ" && value === false) return "must be false";
  return `${operator} ${String(value)}`;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "missing";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}
