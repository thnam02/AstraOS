"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  generateLearningDataset,
  getLearningOverview,
  trainLearningModels,
} from "@/lib/api";
import { formatAudCents } from "@/lib/money";
import type {
  LearningOverview,
  LearningTrainResponse,
} from "@/types";

const DISCLAIMER =
  "This model is trained on simulated buyer-agent outcomes and is included to demonstrate AstraOS's learning architecture. It should not be interpreted as a real-world conversion model.";

function metric(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(3);
}

export function LearnWorkbench() {
  const [overview, setOverview] = useState<LearningOverview | null>(null);
  const [train, setTrain] = useState<LearningTrainResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [target, setTarget] = useState(200);

  async function refresh() {
    setOverview(await getLearningOverview());
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Unable to load learning");
    });
  }, []);

  async function onGenerate() {
    setBusy(true);
    setError(null);
    try {
      await generateLearningDataset({
        interaction_count_target: target,
        seed: 2026,
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dataset generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function onTrain() {
    if (!overview?.dataset) return;
    setBusy(true);
    setError(null);
    try {
      const result = await trainLearningModels({
        dataset_id: overview.dataset.dataset_id,
        seed: 2026,
      });
      setTrain(result);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Training failed");
    } finally {
      setBusy(false);
    }
  }

  const reports =
    train?.reports ?? overview?.latest_training?.reports ?? {};
  const ablations = train?.ablations ?? overview?.latest_training?.ablations;
  const hero = train?.hero_mission ?? overview?.latest_training?.hero_mission;
  const selected =
    train?.selected_algorithm ?? overview?.latest_training?.selected;
  const calibration =
    reports.LOGISTIC_REGRESSION?.calibration ??
    reports.GRADIENT_BOOSTING?.calibration ??
    [];
  const associations = overview?.associations ?? [];

  return (
    <div className="space-y-8">
      <p className="border border-warning/30 bg-warning/5 px-3 py-2 text-xs text-warning">
        {DISCLAIMER}
      </p>
      <p className="text-xs text-muted">
        Judge demo: inspect the pre-trained synthetic model. Do not train live
        unless asked.
      </p>

      <ol className="grid gap-2 text-sm md:grid-cols-5">
        {(overview?.maturity ?? []).map((item) => (
          <li key={item.id} className="border border-line bg-surface p-3">
            <p className="text-[11px] tracking-[0.12em] text-muted">{item.state}</p>
            <p className="mt-1 font-medium">{item.label}</p>
          </li>
        ))}
      </ol>

      <div className="text-sm leading-7 text-muted">
        INTENT → OFFER → BUYER AGENT → OUTCOME → LEARNING DATA → RESPONSE MODEL
      </div>

      <section className="grid gap-4 md:grid-cols-4">
        <Stat
          label="Synthetic interactions"
          value={overview?.dataset?.interaction_count ?? 0}
        />
        <Stat label="Selected" value={overview?.dataset?.positive_count ?? 0} />
        <Stat label="Not selected" value={overview?.dataset?.negative_count ?? 0} />
        <Stat
          label="Missions"
          value={overview?.dataset?.metadata.mission_count ?? 0}
        />
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <label className="text-xs text-muted">
          Target rows
          <input
            className="control ml-2 w-24 px-2 py-1"
            type="number"
            min={40}
            max={5000}
            value={target}
            onChange={(event) => setTarget(Number(event.target.value))}
          />
        </label>
        <button
          type="button"
          className="btn-primary"
          onClick={() => void onGenerate()}
          disabled={busy}
        >
          {busy ? "Working…" : "Generate synthetic dataset"}
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => void onTrain()}
          disabled={busy || !overview?.dataset}
        >
          Train models
        </button>
      </div>

      {overview?.dataset?.metadata.audit ? (
        <section>
          <h2 className="text-sm font-semibold">Synthetic dataset audit</h2>
          <p className="text-xs text-muted">Not production customer data.</p>
          <div className="mt-2 grid gap-3 text-xs md:grid-cols-3">
            <AuditMap
              title="Buyer profiles"
              values={overview.dataset.metadata.audit.buyer_profiles ?? {}}
            />
            <AuditMap
              title="Scenarios"
              values={overview.dataset.metadata.audit.scenario_tags ?? {}}
            />
            <AuditMap
              title="Delivery"
              values={overview.dataset.metadata.audit.deliveries ?? {}}
            />
          </div>
        </section>
      ) : null}

      <section>
        <h2 className="text-sm font-semibold">Model comparison</h2>
        <p className="text-xs text-muted">
          Held-out synthetic test. Cold-start utility may be strong because it
          generated the labels.
        </p>
        <table className="mt-2 w-full text-left text-xs">
          <thead>
            <tr className="border-b border-line text-muted">
              <th className="py-2">Model</th>
              <th>Log loss</th>
              <th>Brier</th>
              <th>ROC AUC</th>
              <th>Top-1</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {Object.keys(reports).length
              ? Object.entries(reports).map(([name, row]) => (
                  <tr key={name} className="border-b border-line">
                    <td className="py-2">{name}</td>
                    <td>{metric(row.classification.log_loss)}</td>
                    <td>{metric(row.classification.brier)}</td>
                    <td>{metric(row.classification.roc_auc)}</td>
                    <td>{metric(row.ranking.top1)}</td>
                    <td>
                      {selected === name
                        ? "ACTIVE_EXPERIMENTAL"
                        : name.includes("HEURISTIC") || name.includes("COLD")
                          ? "BASELINE"
                          : "CANDIDATE"}
                    </td>
                  </tr>
                ))
              : overview?.models.map((model) => (
                  <tr key={model.model_id} className="border-b border-line">
                    <td className="py-2">{model.algorithm}</td>
                    <td>{metric(model.metrics.classification?.log_loss)}</td>
                    <td>{metric(model.metrics.classification?.brier)}</td>
                    <td>{metric(model.metrics.classification?.roc_auc)}</td>
                    <td>{metric(model.metrics.ranking?.top1)}</td>
                    <td>{model.status}</td>
                  </tr>
                ))}
          </tbody>
        </table>
      </section>

      {calibration.length ? (
        <section className="h-[240px] border border-line bg-surface p-3">
          <p className="mb-2 text-xs text-muted">
            Synthetic calibration — predicted vs observed simulated selection.
          </p>
          <ResponsiveContainer width="100%" height="90%">
            <LineChart
              data={calibration.map((item) => ({
                x: item.predicted,
                y: item.observed,
              }))}
            >
              <CartesianGrid stroke="#e4e4e0" />
              <XAxis dataKey="x" name="Predicted" />
              <YAxis dataKey="y" name="Observed" />
              <Tooltip />
              <Line type="monotone" dataKey="y" stroke="#171717" dot />
            </LineChart>
          </ResponsiveContainer>
        </section>
      ) : null}

      {associations.length ? (
        <section>
          <h2 className="text-sm font-semibold">
            Model association / feature importance
          </h2>
          <p className="text-xs text-muted">
            Associations in synthetic training data — not conversion drivers.
          </p>
          <ul className="mt-2 space-y-1 text-xs">
            {associations.slice(0, 10).map((item) => (
              <li key={item.feature} className="flex justify-between border-b border-line py-1">
                <span>{item.feature}</span>
                <span className="tabular-nums">{item.coefficient.toFixed(3)}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {ablations ? (
        <section>
          <h2 className="text-sm font-semibold">Feature ablation</h2>
          <table className="mt-2 w-full text-left text-xs">
            <thead>
              <tr className="border-b border-line text-muted">
                <th className="py-2">Subset</th>
                <th>Brier</th>
                <th>Top-1</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(ablations).map(([name, row]) => (
                <tr key={name} className="border-b border-line">
                  <td className="py-2">{name}</td>
                  <td>{metric(row.classification.brier)}</td>
                  <td>{metric(row.ranking.top1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {hero?.offers?.length ? (
        <section>
          <h2 className="text-sm font-semibold">Held-out mission</h2>
          <p className="text-xs text-muted">{hero.note}</p>
          <table className="mt-2 w-full text-left text-xs">
            <thead>
              <tr className="border-b border-line text-muted">
                <th className="py-2">Offer</th>
                <th>Cold-start utility</th>
                <th>Learned score</th>
                <th>Outcome</th>
              </tr>
            </thead>
            <tbody>
              {hero.offers.map((row, index) => (
                <tr key={index} className="border-b border-line">
                  <td className="py-2">
                    {formatAudCents(row.price_cents)} · {row.delivery_days}d ·{" "}
                    {row.warranty_months}m
                  </td>
                  <td>{row.cold_start_utility.toFixed(3)}</td>
                  <td>{row.learned_score.toFixed(3)}</td>
                  <td>{row.selected ? "SELECTED" : "NOT SELECTED"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      <section>
        <h2 className="text-sm font-semibold">Intent → Offer → Outcome</h2>
        <p className="text-xs text-muted">
          Synthetic Arena rows. Not observed customer purchases.
        </p>
        <table className="mt-2 w-full text-left text-xs">
          <thead>
            <tr className="border-b border-line text-muted">
              <th className="py-2">Intent</th>
              <th>Offer</th>
              <th>Outcome</th>
            </tr>
          </thead>
          <tbody>
            {(overview?.sample_interactions ?? []).map((row, index) => (
              <tr key={index} className="border-b border-line">
                <td className="max-w-xs py-2">{row.profile}</td>
                <td>
                  {formatAudCents(row.price_cents)} · {row.delivery} · {row.warranty}
                </td>
                <td>
                  {row.outcome} / {row.source}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {error ? <p className="text-sm text-danger">{error}</p> : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="border border-line bg-surface p-3">
      <p className="text-[11px] tracking-[0.12em] text-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value.toLocaleString()}</p>
    </div>
  );
}

function AuditMap({
  title,
  values,
}: {
  title: string;
  values: Record<string, number>;
}) {
  return (
    <div className="border border-line p-3">
      <p className="font-medium">{title}</p>
      <ul className="mt-1 space-y-1 text-muted">
        {Object.entries(values)
          .slice(0, 8)
          .map(([key, count]) => (
            <li key={key}>
              {key}: {count}
            </li>
          ))}
      </ul>
    </div>
  );
}
