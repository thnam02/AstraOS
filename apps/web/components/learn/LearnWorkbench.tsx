"use client";

import { useEffect, useId, useState } from "react";
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
  AstraDataTable,
  AstraEmptyState,
  AstraErrorState,
  AstraLoadingState,
  AstraPanel,
  AstraSectionHeader,
  AstraStatusBadge,
  type AstraTone,
} from "@/components/astra";
import { SectionTabs } from "@/components/shared/SectionTabs";
import { Drawer } from "@/components/shared/Drawer";

import {
  generateLearningDataset,
  getLearningOverview,
  trainLearningModels,
} from "@/lib/api";
import {
  LEARN_STATUS,
  LEARN_STORY,
  learnCapabilityStatusLabel,
  type LearnCapabilityState,
} from "@/lib/decisionNarrative";
import { formatCount, formatUtilityShort, humanizeEnum } from "@/lib/format";
import { formatAudCents } from "@/lib/money";
import type { LearningOverview, LearningTrainResponse } from "@/types";

/** Token-mapped chart colors (Recharts needs hex; map to Astra tokens). */
const CHART_MARK = "#1f6b5a"; // --color-mark
const CHART_GRID = "#ebe8e1"; // near --color-line / canvas tint
const CHART_AXIS = "#5c5a54"; // muted ink for axes

type LabPhase = "idle" | "generating" | "training";

function metric(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return formatUtilityShort(value);
}

function capabilityTone(state: LearnCapabilityState): AstraTone {
  if (state === "ACTIVE") return "positive";
  if (state === "PRIMARY") return "info";
  if (state === "EXPERIMENTAL") return "warning";
  return "neutral";
}

function safeMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message.trim()) {
    const msg = err.message.trim();
    if (msg.length > 180 || msg.startsWith("{") || msg.includes("Traceback")) {
      return fallback;
    }
    return msg;
  }
  return fallback;
}

export function LearnWorkbench() {
  const targetId = useId();
  const [labOpen, setLabOpen] = useState(false);
  const [technical, setTechnical] = useState(false);
  const [samplePage, setSamplePage] = useState(0);
  const [missionPage, setMissionPage] = useState(0);
  const [modelPage, setModelPage] = useState(0);
  const [overview, setOverview] = useState<LearningOverview | null>(null);
  const [train, setTrain] = useState<LearningTrainResponse | null>(null);
  const [phase, setPhase] = useState<LabPhase>("idle");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<{
    kind: "generate" | "train";
    message: string;
  } | null>(null);
  const [target, setTarget] = useState(200);

  async function refresh() {
    setOverview(await getLearningOverview());
  }

  useEffect(() => {
    let cancelled = false;
    void getLearningOverview()
      .then((data) => {
        if (!cancelled) {
          setOverview(data);
          setLoadError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLoadError(
            safeMessage(err, "Unable to load outcome learning overview."),
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onGenerate() {
    setPhase("generating");
    setActionError(null);
    try {
      await generateLearningDataset({
        interaction_count_target: target,
        seed: 2026,
      });
      await refresh();
    } catch (err) {
      setActionError({
        kind: "generate",
        message: safeMessage(
          err,
          "Dataset generation failed. Check the API and retry.",
        ),
      });
    } finally {
      setPhase("idle");
    }
  }

  async function onTrain() {
    if (!overview?.dataset) return;
    setPhase("training");
    setActionError(null);
    try {
      const result = await trainLearningModels({
        dataset_id: overview.dataset.dataset_id,
        seed: 2026,
      });
      setTrain(result);
      await refresh();
    } catch (err) {
      setActionError({
        kind: "train",
        message: safeMessage(
          err,
          "Training failed. Retry after the dataset is ready.",
        ),
      });
    } finally {
      setPhase("idle");
    }
  }

  const reports = train?.reports ?? overview?.latest_training?.reports ?? {};
  const ablations = train?.ablations ?? overview?.latest_training?.ablations;
  const hero = train?.hero_mission ?? overview?.latest_training?.hero_mission;
  const selected =
    train?.selected_algorithm ?? overview?.latest_training?.selected;
  const calibration =
    reports.LOGISTIC_REGRESSION?.calibration ??
    reports.GRADIENT_BOOSTING?.calibration ??
    [];
  const associations = overview?.associations ?? [];
  const hasDataset = Boolean(overview?.dataset);
  const hasModelResults =
    Object.keys(reports).length > 0 || (overview?.models.length ?? 0) > 0;
  const busy = phase !== "idle";

  if (loading && !overview) {
    return (
      <AstraLoadingState
        title="Loading outcome learning"
        steps={[
          "Reading capability status",
          "Checking synthetic datasets",
          "Ready for experimental lab",
        ]}
      />
    );
  }

  if (loadError && !overview) {
    return (
      <div className="space-y-6">
        <AstraSectionHeader
          eyebrow="Learn"
          title="Outcome learning"
          description="How future merchant decisions can improve from observed outcomes."
        />
        <AstraErrorState
          title="Unable to load outcome learning"
          message={loadError}
          next="Confirm the API is reachable, then reload this page."
        />
        <button
          type="button"
          className="btn-primary"
          onClick={() => window.location.reload()}
        >
          Reload
        </button>
      </div>
    );
  }

  const modelCount =
    Object.keys(reports).length || (overview?.models.length ?? 0);
  const missionCount = hero?.offers?.length ?? 0;
  const sampleCount = overview?.sample_interactions?.length ?? 0;
  const modelOffset =
    Math.min(modelPage, Math.max(0, Math.ceil(modelCount / 5) - 1)) * 5;
  const missionOffset =
    Math.min(missionPage, Math.max(0, Math.ceil(missionCount / 5) - 1)) * 5;
  const sampleOffset =
    Math.min(samplePage, Math.max(0, Math.ceil(sampleCount / 5) - 1)) * 5;

  return (
    <div className="space-y-4">
      <AstraSectionHeader
        eyebrow="Learn"
        title="Outcome learning"
        description="How buyer intent, merchant offers, and observed outcomes can improve future decisions."
      />
      <div className="grid items-stretch gap-5 lg:grid-cols-2">
        <AstraPanel className="flex flex-col">
          <h2 className="text-xl font-semibold">Outcome learning flow</h2>
          <p className="mt-2 text-sm text-muted">
            From a buyer request to future decision support.
          </p>
          <ol
            className="mt-4 grid flex-1 auto-rows-fr"
            aria-label="Outcome learning flow"
          >
            {LEARN_STORY.map((item, index) => (
              <li
                key={item.id}
                className="grid grid-cols-[2rem_minmax(0,1fr)] items-center gap-3 border-t border-line py-2.5"
              >
                <span className="font-mono text-sm tabular-nums text-mark">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <h3 className="text-sm font-semibold">{item.label}</h3>
                  <p className="mt-0.5 text-sm text-muted">{item.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </AstraPanel>
        <AstraPanel className="flex flex-col">
          <h2 className="text-xl font-semibold">Current capability</h2>
          <p className="mt-2 text-sm text-muted">
            What is active today, experimental, and still to come.
          </p>
          <dl className="mt-4 grid flex-1 auto-rows-fr">
            {LEARN_STATUS.map((item) => (
              <div
                key={item.label}
                className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-t border-line py-3"
              >
                <dt className="text-sm font-medium">{item.label}</dt>
                <dd>
                  <AstraStatusBadge tone={capabilityTone(item.state)}>
                    {learnCapabilityStatusLabel(item.state)}
                  </AstraStatusBadge>
                </dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 border-t border-line pt-3 text-xs leading-5 text-muted">
            LIVE uses transparent cold-start scoring. Learned models use
            synthetic outcomes and remain experimental until real B2A outcomes
            exist.
          </p>
        </AstraPanel>
      </div>
      <aside
        className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3"
        aria-label="Experimental learning lab"
      >
        <div>
          <p className="text-sm font-medium">Experimental learning lab</p>
          <p className="mt-1 text-xs text-muted">
            {busy
              ? phase === "generating"
                ? "Generating synthetic outcomes…"
                : "Training experimental models…"
              : "Generate datasets, train models, and inspect synthetic evaluation results."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs text-muted">
            {hasDataset
              ? `${formatCount(overview?.dataset?.interaction_count ?? 0)} synthetic rows`
              : "No dataset"}
          </span>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setLabOpen(true)}
          >
            Open learning lab →
          </button>
        </div>
      </aside>
      <Drawer
        wide
        open={labOpen}
        title="Experimental learning lab"
        onClose={() => setLabOpen(false)}
      >
        <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <AstraPanel tone="primary">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold">Learning lab</h2>
              <AstraStatusBadge tone={hasDataset ? "warning" : "neutral"}>
                {hasDataset ? "Dataset ready" : "No dataset"}
              </AstraStatusBadge>
            </div>
            {actionError ? (
              <div className="mt-3">
                <AstraErrorState
                  title={
                    actionError.kind === "train"
                      ? "Training failed"
                      : "Dataset generation failed"
                  }
                  message={actionError.message}
                  next="Retry when the API is available."
                />
              </div>
            ) : null}
            {busy ? (
              <p
                className="mt-3 text-sm font-medium"
                role="status"
                aria-live="polite"
              >
                {phase === "generating"
                  ? "Generating synthetic outcomes…"
                  : "Training experimental models…"}
              </p>
            ) : null}
            {overview?.dataset ? (
              <dl className="mt-4 grid grid-cols-2 gap-3">
                {[
                  {
                    label: "Interactions",
                    value: overview.dataset.interaction_count,
                  },
                  {
                    label: "Missions",
                    value: overview.dataset.metadata.mission_count ?? 0,
                  },
                  { label: "Selected", value: overview.dataset.positive_count },
                  {
                    label: "Not selected",
                    value: overview.dataset.negative_count,
                  },
                ].map((item) => (
                  <div key={item.label}>
                    <dt className="text-xs text-muted">{item.label}</dt>
                    <dd className="mt-1 font-mono text-lg tabular-nums">
                      {formatCount(item.value)}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="mt-3 text-sm text-muted">
                Generate a dataset to start comparing response models.
              </p>
            )}
            <div className="mt-4 border-t border-line pt-4">
              <label htmlFor={targetId} className="text-xs text-muted">
                Target synthetic rows
              </label>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  id={targetId}
                  className="control w-24 px-2 py-2 text-sm"
                  type="number"
                  min={40}
                  max={5000}
                  value={target}
                  disabled={busy}
                  onChange={(event) =>
                    setTarget(Number(event.target.value) || 40)
                  }
                />
                <button
                  type="button"
                  className={hasDataset ? "btn-ghost" : "btn-primary"}
                  disabled={busy}
                  onClick={() => void onGenerate()}
                >
                  {phase === "generating"
                    ? "Generating…"
                    : hasDataset
                      ? "New dataset"
                      : "Generate dataset"}
                </button>
              </div>
            </div>
            <div className="mt-4 border-t border-line pt-4">
              <p className="eyebrow">Model training</p>
              <p className="mt-2 text-xs leading-5 text-muted">
                Compare candidate algorithms on held-out synthetic outcomes.
              </p>
              <button
                type="button"
                className="btn-primary mt-3"
                disabled={busy || !hasDataset}
                aria-describedby={
                  !hasDataset ? `${targetId}-train-hint` : undefined
                }
                onClick={() => void onTrain()}
              >
                {phase === "training"
                  ? "Training…"
                  : "Train experimental model"}
              </button>
              {!hasDataset ? (
                <p
                  id={`${targetId}-train-hint`}
                  className="mt-2 text-xs text-muted"
                >
                  Generate a dataset before training.
                </p>
              ) : null}
              {hasModelResults ? (
                <p className="mt-3 text-sm">
                  <span className="text-muted">Selected algorithm</span>
                  <br />
                  <span className="font-medium">
                    {selected ? humanizeEnum(selected) : "—"}
                  </span>
                </p>
              ) : null}
            </div>
            {hasDataset || hasModelResults ? (
              <button
                type="button"
                className="btn-quiet mt-3"
                onClick={() => setTechnical(true)}
              >
                Inspect technical evaluation →
              </button>
            ) : null}
          </AstraPanel>
          <SectionTabs
            equalHeight
            label="Learning results"
            items={[
              {
                label: "Model evaluation",
                content: (
                  <AstraPanel>
                    {hasModelResults ? (
                      <div className="space-y-2">
                        <p className="text-xs tracking-[0.08em] text-muted">
                          MODEL EVALUATION
                        </p>
                        <p className="mt-1 type-small text-muted">
                          Held-out synthetic test metrics only. Cold-start
                          utility may score strongly because it generated the
                          labels. Not production uplift.
                        </p>
                        <AstraDataTable
                          bordered={false}
                          className="mt-3 text-xs"
                        >
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
                              ? Object.entries(reports)
                                  .slice(modelOffset, modelOffset + 5)
                                  .map(([name, row]) => (
                                    <tr
                                      key={name}
                                      className="border-b border-line"
                                    >
                                      <td className="py-2">
                                        {humanizeEnum(name)}
                                      </td>
                                      <td>
                                        {metric(row.classification.log_loss)}
                                      </td>
                                      <td>
                                        {metric(row.classification.brier)}
                                      </td>
                                      <td>
                                        {metric(row.classification.roc_auc)}
                                      </td>
                                      <td>{metric(row.ranking.top1)}</td>
                                      <td>
                                        {selected === name
                                          ? "Selected · Experimental"
                                          : name.includes("HEURISTIC") ||
                                              name.includes("COLD")
                                            ? "Baseline"
                                            : "Candidate"}
                                      </td>
                                    </tr>
                                  ))
                              : overview?.models
                                  .slice(modelOffset, modelOffset + 5)
                                  .map((model) => (
                                    <tr
                                      key={model.model_id}
                                      className="border-b border-line"
                                    >
                                      <td className="py-2">
                                        {humanizeEnum(model.algorithm)}
                                      </td>
                                      <td>
                                        {metric(
                                          model.metrics.classification
                                            ?.log_loss,
                                        )}
                                      </td>
                                      <td>
                                        {metric(
                                          model.metrics.classification?.brier,
                                        )}
                                      </td>
                                      <td>
                                        {metric(
                                          model.metrics.classification?.roc_auc,
                                        )}
                                      </td>
                                      <td>
                                        {metric(model.metrics.ranking?.top1)}
                                      </td>
                                      <td>{humanizeEnum(model.status)}</td>
                                    </tr>
                                  ))}
                          </tbody>
                        </AstraDataTable>
                      </div>
                    ) : null}

                    {!hasModelResults ? (
                      <AstraEmptyState
                        title="No trained model yet"
                        body="Generate a dataset and train a model to compare held-out metrics here."
                      />
                    ) : null}
                    <LearningPages
                      label="Models"
                      count={modelCount}
                      offset={modelOffset}
                      onPage={setModelPage}
                    />
                  </AstraPanel>
                ),
              },
              {
                label: "Held-out mission",
                content: (
                  <AstraPanel>
                    {hero?.offers?.length ? (
                      <div className="space-y-2">
                        <p className="text-xs tracking-[0.08em] text-muted">
                          HELD-OUT MISSION
                        </p>
                        {hero.note ? (
                          <p className="mt-1 type-small text-muted">
                            {hero.note}
                          </p>
                        ) : null}
                        <AstraDataTable
                          bordered={false}
                          className="mt-3 text-xs"
                        >
                          <thead>
                            <tr className="border-b border-line text-muted">
                              <th className="py-2">Offer</th>
                              <th>Cold-start utility</th>
                              <th>Learned score</th>
                              <th>Outcome</th>
                            </tr>
                          </thead>
                          <tbody>
                            {hero.offers
                              .slice(missionOffset, missionOffset + 5)
                              .map((row, index) => (
                                <tr
                                  key={index}
                                  className="border-b border-line"
                                >
                                  <td className="py-2">
                                    {formatAudCents(row.price_cents)} ·{" "}
                                    {row.delivery_days}d · {row.warranty_months}
                                    m
                                  </td>
                                  <td>{row.cold_start_utility.toFixed(3)}</td>
                                  <td>{row.learned_score.toFixed(3)}</td>
                                  <td>
                                    {row.selected ? "Selected" : "Not selected"}
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </AstraDataTable>
                      </div>
                    ) : null}

                    {!missionCount ? (
                      <AstraEmptyState
                        title="No held-out mission yet"
                        body="Training produces a comparison of cold-start utility and learned scores."
                      />
                    ) : null}
                    <LearningPages
                      label="Mission offers"
                      count={missionCount}
                      offset={missionOffset}
                      onPage={setMissionPage}
                    />
                  </AstraPanel>
                ),
              },
              {
                label: "Sample outcomes",
                content: (
                  <AstraPanel>
                    {(overview?.sample_interactions?.length ?? 0) > 0 ? (
                      <div className="space-y-2">
                        <p className="text-xs tracking-[0.08em] text-muted">
                          SAMPLE SYNTHETIC OUTCOMES
                        </p>
                        <p className="mt-1 type-small text-muted">
                          Synthetic Arena rows. Not observed customer purchases.
                        </p>
                        <AstraDataTable
                          bordered={false}
                          className="mt-3 text-xs"
                        >
                          <thead>
                            <tr className="border-b border-line text-muted">
                              <th className="py-2">Intent</th>
                              <th>Offer</th>
                              <th>Outcome</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(overview?.sample_interactions ?? [])
                              .slice(sampleOffset, sampleOffset + 5)
                              .map((row, index) => (
                                <tr
                                  key={index}
                                  className="border-b border-line"
                                >
                                  <td className="max-w-xs py-2">
                                    {row.profile}
                                  </td>
                                  <td>
                                    {formatAudCents(row.price_cents)} ·{" "}
                                    {row.delivery} · {row.warranty}
                                  </td>
                                  <td>
                                    {row.outcome} / {row.source}
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </AstraDataTable>
                      </div>
                    ) : null}

                    {!sampleCount ? (
                      <AstraEmptyState
                        title="No sample outcomes yet"
                        body="Generate a dataset to inspect its synthetic interactions."
                      />
                    ) : null}
                    <LearningPages
                      label="Sample outcomes"
                      count={sampleCount}
                      offset={sampleOffset}
                      onPage={setSamplePage}
                    />
                  </AstraPanel>
                ),
              },
            ]}
          />
        </div>
      </Drawer>
      <Drawer
        open={technical}
        title="Technical evaluation"
        onClose={() => setTechnical(false)}
      >
        {hasDataset || hasModelResults ? (
          <div className="space-y-4">
            <p className="mt-2 type-small text-muted">
              Internal evaluation detail for the experimental synthetic
              pipeline.
            </p>

            {overview?.dataset?.metadata.audit ? (
              <div className="mt-4">
                <p className="text-xs tracking-[0.08em] text-muted">
                  DATASET AUDIT
                </p>
                <div className="mt-2 grid gap-3 text-xs md:grid-cols-3">
                  <AuditMap
                    title="Buyer profiles"
                    values={
                      overview.dataset.metadata.audit.buyer_profiles ?? {}
                    }
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
              </div>
            ) : null}

            {calibration.length ? (
              <div className="mt-4 h-[220px] border border-line bg-canvas p-3">
                <p className="mb-2 text-xs text-muted">
                  Synthetic calibration — predicted vs observed simulated
                  selection.
                </p>
                <ResponsiveContainer width="100%" height="85%">
                  <LineChart
                    data={calibration.map((item) => ({
                      x: item.predicted,
                      y: item.observed,
                    }))}
                  >
                    <CartesianGrid stroke={CHART_GRID} />
                    <XAxis dataKey="x" name="Predicted" stroke={CHART_AXIS} />
                    <YAxis dataKey="y" name="Observed" stroke={CHART_AXIS} />
                    <Tooltip />
                    <Line type="monotone" dataKey="y" stroke={CHART_MARK} dot />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : null}

            {associations.length ? (
              <div className="mt-4">
                <p className="text-xs tracking-[0.08em] text-muted">
                  FEATURE ASSOCIATIONS
                </p>
                <p className="mt-1 type-small text-muted">
                  Associations in synthetic training data — not conversion
                  drivers.
                </p>
                <ul className="mt-2 space-y-1 text-xs">
                  {associations.slice(0, 10).map((item) => (
                    <li
                      key={item.feature}
                      className="flex justify-between border-b border-line py-1"
                    >
                      <span>{item.feature}</span>
                      <span className="tabular-nums">
                        {item.coefficient.toFixed(3)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {ablations ? (
              <div className="mt-4">
                <p className="text-xs tracking-[0.08em] text-muted">
                  FEATURE ABLATION
                </p>
                <AstraDataTable bordered={false} className="mt-2 text-xs">
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
                </AstraDataTable>
              </div>
            ) : null}
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}

function LearningPages({
  label,
  count,
  offset,
  onPage,
}: {
  label: string;
  count: number;
  offset: number;
  onPage: (page: number) => void;
}) {
  if (count <= 5) return null;
  return (
    <nav
      aria-label={`${label} pages`}
      className="mt-3 flex items-center justify-between gap-3 text-xs"
    >
      <button
        type="button"
        className="btn-quiet disabled:opacity-40"
        disabled={offset === 0}
        onClick={() => onPage(offset / 5 - 1)}
      >
        Previous
      </button>
      <span className="text-muted">
        {offset + 1}–{Math.min(offset + 5, count)} of {count}
      </span>
      <button
        type="button"
        className="btn-quiet disabled:opacity-40"
        disabled={offset + 5 >= count}
        onClick={() => onPage(offset / 5 + 1)}
      >
        Next
      </button>
    </nav>
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
    <div className="border border-line px-3 py-2">
      <p className="font-medium">{title}</p>
      <ul className="mt-1 space-y-1 text-muted">
        {Object.entries(values)
          .slice(0, 8)
          .map(([key, count]) => (
            <li key={key}>
              {key}: {formatCount(count)}
            </li>
          ))}
      </ul>
    </div>
  );
}
