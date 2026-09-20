"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  AstraEmptyState,
  AstraErrorState,
  AstraLoadingState,
  AstraPanel,
  AstraSectionHeader,
  AstraStatusBadge,
} from "@/components/astra";
import { SectionTabs } from "@/components/shared/SectionTabs";
import { Drawer } from "@/components/shared/Drawer";

import { ExchangeInspector } from "@/components/integrations/ExchangeInspector";
import {
  getAgentActivity,
  getAgentCapabilities,
  getReady,
  openApiDocsUrl,
} from "@/lib/api";
import {
  AGENT_API_REFERENCE,
  activityKindLabel,
  channelLabel,
  operationPresentation,
} from "@/lib/integrationsDisplay";
import { formatAudCents } from "@/lib/money";
import { humanizeEnum } from "@/lib/format";
import type {
  AgentActivityItem,
  AgentCapabilities,
  ReadyResponse,
} from "@/types";

export function IntegrationsWorkbench() {
  const [capabilities, setCapabilities] = useState<AgentCapabilities | null>(
    null,
  );
  const [ready, setReady] = useState<ReadyResponse | null>(null);
  const [activity, setActivity] = useState<AgentActivityItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [showReadiness, setShowReadiness] = useState(false);
  const [inspect, setInspect] = useState<AgentActivityItem | null>(null);

  const loadCore = useCallback(async () => {
    const [caps, readiness] = await Promise.all([
      getAgentCapabilities(),
      getReady(),
    ]);
    setCapabilities(caps);
    setReady(readiness);
  }, []);

  const loadActivity = useCallback(async () => {
    try {
      const feed = await getAgentActivity(25);
      setActivity(feed.items);
      setActivityError(null);
    } catch {
      setActivity(null);
      setActivityError("Unable to load recent agent activity.");
    }
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return loadCore()
      .then(() => loadActivity())
      .catch(() => {
        setError("Unable to load agent API status.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [loadActivity, loadCore]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getAgentCapabilities(), getReady()])
      .then(async ([caps, readiness]) => {
        if (cancelled) return;
        setCapabilities(caps);
        setReady(readiness);
        try {
          const feed = await getAgentActivity(25);
          if (!cancelled) {
            setActivity(feed.items);
            setActivityError(null);
          }
        } catch {
          if (!cancelled) {
            setActivity(null);
            setActivityError("Unable to load recent agent activity.");
          }
        }
      })
      .catch(() => {
        if (!cancelled) setError("Unable to load agent API status.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading && !capabilities && !error) {
    return (
      <AstraLoadingState
        title="Loading agent capabilities"
        steps={[
          "Reading Agent API capabilities",
          "Checking readiness",
          "Loading recent activity",
        ]}
      />
    );
  }

  const mcpAvailable = Boolean(capabilities?.protocol?.includes("MCP"));
  const apiOnline = ready?.status === "ready" || ready?.status === "degraded";
  const operations = capabilities
    ? operationPresentation(capabilities.operations)
    : [];

  const pageSize = 4;
  const lastPage = Math.max(
    0,
    Math.ceil((activity?.length ?? 0) / pageSize) - 1,
  );
  const currentPage = Math.min(page, lastPage);
  const visibleActivity =
    activity?.slice(currentPage * pageSize, (currentPage + 1) * pageSize) ?? [];

  const activityPanel = (
    <AstraPanel className="integration-panel">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="eyebrow">Recent agent activity</p>
          <p className="mt-1 text-xs text-muted">
            Latest {activity?.length ?? 0} sessions · agent requests and
            operator tests
          </p>
        </div>
        <Link href="/" className="btn-ghost">
          Create test request
        </Link>
      </div>
      {activityError ? (
        <AstraErrorState
          title="Activity unavailable"
          message={activityError}
          next="Refresh to retry loading agent activity."
        />
      ) : activity?.length === 0 ? (
        <AstraEmptyState
          title="No agent activity yet"
          body="Create a test request or connect a buyer agent to see exchanges here."
        />
      ) : (
        <ul className="divide-y divide-line border-y border-line">
          {visibleActivity.map((item) => {
            const ref =
              item.order_number ??
              item.request_id ??
              item.proposal_id ??
              item.negotiation_session_id;
            const shortRef =
              item.order_number ?? ref.replace(/-/g, "").slice(0, 8);
            const when = new Date(item.occurred_at);
            return (
              <li
                key={item.negotiation_session_id}
                className="integration-activity-row grid grid-cols-[minmax(0,1fr)_auto] items-center gap-5 py-3"
              >
                <div className="min-w-0">
                  <p className="integration-event-title text-base font-semibold">
                    {activityKindLabel(item.kind)}
                  </p>
                  <p
                    className="line-clamp-2 text-sm leading-5 text-muted"
                    title={item.intent_summary}
                  >
                    {item.intent_summary}
                  </p>
                  <p className="mt-2 flex flex-wrap gap-x-3 text-xs text-muted">
                    <time
                      dateTime={item.occurred_at}
                      title={when.toLocaleString()}
                    >
                      {when.toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                      })}{" "}
                      {when.toLocaleTimeString(undefined, {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </time>
                    <span>{channelLabel(item.channel)}</span>
                    <span className="font-mono" title={ref}>
                      {shortRef}
                    </span>
                    <span>{humanizeEnum(item.status)}</span>
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-base font-medium tabular-nums">
                    {item.total_amount_cents != null
                      ? formatAudCents(item.total_amount_cents)
                      : "—"}
                  </p>
                  <button
                    type="button"
                    className="btn-quiet"
                    aria-label={`Inspect exchange ${shortRef}`}
                    onClick={() => setInspect(item)}
                  >
                    Inspect
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {!activityError && (activity?.length ?? 0) > 0 ? (
        <nav
          className="mt-3 flex items-center justify-between text-xs"
          aria-label="Activity pages"
        >
          <button
            type="button"
            className="btn-quiet disabled:opacity-40"
            disabled={currentPage === 0}
            onClick={() => setPage(currentPage - 1)}
          >
            Previous
          </button>
          <span className="text-muted">
            {currentPage * pageSize + 1}–
            {Math.min((currentPage + 1) * pageSize, activity!.length)} of{" "}
            {activity!.length}
          </span>
          <button
            type="button"
            className="btn-quiet disabled:opacity-40"
            disabled={currentPage === lastPage}
            onClick={() => setPage(currentPage + 1)}
          >
            Next
          </button>
        </nav>
      ) : null}
    </AstraPanel>
  );

  const capabilitiesPanel = (
    <AstraPanel className="integration-panel flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Agent capabilities</h2>
          <p className="mt-1 text-sm text-muted">
            Operations advertised by the connected API.
          </p>
        </div>
        <span className="shrink-0 font-mono text-sm text-muted">
          {operations.length} operations
        </span>
      </div>
      {operations.length ? (
        <ul className="grid flex-1 auto-rows-fr gap-x-6 sm:grid-cols-2">
          {operations.map((row, index) => (
            <li
              key={row.operation}
              className="flex items-center gap-3 border-t border-line py-3"
            >
              <span className="self-start pt-0.5 font-mono text-xs tabular-nums text-muted">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <p className="text-xs text-muted">{row.group}</p>
                <p className="mt-1 text-base font-medium leading-5">
                  {row.label}
                </p>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">No capabilities loaded.</p>
      )}
      <div className="grid gap-4 border-t border-line pt-4 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        {capabilities?.supported?.length ? (
          <section aria-label="Supported capabilities">
            <p className="eyebrow text-mark">Supported</p>
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {capabilities.supported.map((item) => (
                <li
                  key={item}
                  className="rounded-[var(--radius-control)] bg-canvas px-2 py-1 text-xs leading-4"
                >
                  {item}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {capabilities?.not_supported?.length ? (
          <section aria-label="Capability limits">
            <p className="eyebrow">Not supported</p>
            <ul className="mt-2 space-y-1 text-xs leading-5 text-muted">
              {capabilities.not_supported.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </AstraPanel>
  );

  const referencePanel = (
    <AstraPanel className="integration-panel flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Public REST contract</h2>
          <p className="mt-1 text-sm text-muted">
            Endpoints, methods, and their role in the exchange.
          </p>
        </div>
        <span className="shrink-0 font-mono text-sm text-muted">
          {AGENT_API_REFERENCE.length} endpoints
        </span>
      </div>
      <ul className="grid flex-1 auto-rows-fr divide-y divide-line border-y border-line">
        {AGENT_API_REFERENCE.map((row) => (
          <li
            key={`${row.method}-${row.path}`}
            className="grid grid-cols-[3.5rem_minmax(0,1fr)] items-center gap-x-3 gap-y-1 py-3 xl:grid-cols-[3.5rem_minmax(0,1.2fr)_minmax(0,1fr)]"
          >
            <span className="self-center rounded-[var(--radius-control)] bg-canvas px-2 py-1.5 text-center font-mono text-xs font-semibold">
              {row.method}
            </span>
            <code className="min-w-0 font-mono text-sm leading-5 [overflow-wrap:anywhere]">
              {row.path}
            </code>
            <p className="col-start-2 text-sm leading-5 text-muted xl:col-start-auto">
              {row.purpose}
            </p>
          </li>
        ))}
      </ul>
      <a
        href={openApiDocsUrl()}
        target="_blank"
        rel="noreferrer"
        className="btn-quiet self-start"
      >
        View full request and response schemas →
      </a>
    </AstraPanel>
  );

  return (
    <div className="integrations-workbench space-y-4">
      <AstraSectionHeader
        eyebrow="Integrations"
        title="Connect buyer agents"
        description="One public Agent API for discovery, negotiation, and order execution."
        action={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-ghost"
              disabled={loading}
              onClick={load}
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
            <a
              href={openApiDocsUrl()}
              target="_blank"
              rel="noreferrer"
              className="btn-primary"
            >
              Open API docs
            </a>
          </div>
        }
      />

      {error ? (
        <AstraErrorState
          title="Unable to load agent API status"
          message={error}
          next="Confirm the API is running, then use Refresh to retry."
        />
      ) : null}

      <div
        className="integration-architecture flex flex-wrap items-center gap-x-3 gap-y-2 border-y border-line py-3 text-sm text-muted"
        aria-label="Integration architecture"
      >
        <span className="font-medium text-ink">Buyer agent</span>
        <span className="inline-flex items-center gap-3">
          <span aria-hidden>→</span>
          <span>Agent API</span>
        </span>
        <span className="inline-flex items-center gap-3">
          <span aria-hidden>→</span>
          <span className="font-medium text-ink">AstraOS</span>
        </span>
        <span className="inline-flex items-center gap-3">
          <span aria-hidden>→</span>
          <span>Merchant data + rules</span>
        </span>
      </div>

      <div className="integration-columns grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <aside className="min-w-0 space-y-4" aria-label="Connection status">
          <AstraPanel tone="primary" className="integration-panel">
            <div className="flex items-center justify-between gap-3">
              <p className="eyebrow">Agent API</p>
              {ready ? (
                <AstraStatusBadge
                  tone={
                    ready.status === "ready"
                      ? "positive"
                      : ready.status === "degraded"
                        ? "warning"
                        : "negative"
                  }
                >
                  {ready.status === "degraded"
                    ? "Experimental"
                    : humanizeEnum(ready.status)}
                </AstraStatusBadge>
              ) : (
                <span className="text-xs text-muted">Unavailable</span>
              )}
            </div>
            <dl className="integration-status mt-4 space-y-3 text-base">
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Protocol</dt>
                <dd>{capabilities?.protocol?.join(" · ") ?? "—"}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Version</dt>
                <dd className="font-mono">{capabilities?.version ?? "—"}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Service</dt>
                <dd className="break-all text-right font-mono text-sm">
                  {capabilities?.service ?? "—"}
                </dd>
              </div>
            </dl>
            {!apiOnline && ready ? (
              <p className="mt-3 text-xs text-danger">
                Agent traffic may be unreliable until required checks pass.
              </p>
            ) : null}
            <button
              type="button"
              className="btn-quiet mt-3"
              disabled={!ready}
              onClick={() => setShowReadiness(true)}
            >
              Inspect readiness
            </button>
            {capabilities?.disclaimer ? (
              <p className="mt-2 text-xs leading-5 text-muted">
                {capabilities.disclaimer}
              </p>
            ) : null}
          </AstraPanel>
          <AstraPanel className="integration-panel">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="eyebrow">MCP adapter</p>
              <AstraStatusBadge tone={mcpAvailable ? "positive" : "warning"}>
                {mcpAvailable ? "Available" : "Not advertised"}
              </AstraStatusBadge>
            </div>
            <p className="mt-3 text-sm leading-5 text-muted">
              Optional access for compatible agent clients. Uses the same public
              REST contract and merchant rules.
            </p>
          </AstraPanel>
        </aside>
        <SectionTabs
          equalHeight
          label="Integration workspace"
          items={[
            { label: "Activity", content: activityPanel },
            { label: "Capabilities", content: capabilitiesPanel },
            { label: "API reference", content: referencePanel },
          ]}
        />
      </div>

      <Drawer
        open={showReadiness}
        title="Agent API readiness"
        onClose={() => setShowReadiness(false)}
      >
        <ul className="divide-y divide-line">
          {ready?.checks.map((check) => (
            <li key={check.name} className="py-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium">
                  {humanizeEnum(check.name)}
                </p>
                <AstraStatusBadge
                  tone={
                    check.ok
                      ? "positive"
                      : check.required
                        ? "negative"
                        : "warning"
                  }
                >
                  {check.ok
                    ? "Passed"
                    : check.required
                      ? "Failed"
                      : "Unavailable"}
                </AstraStatusBadge>
              </div>
              <p className="mt-1 break-words text-xs text-muted">
                {check.detail}
              </p>
            </li>
          ))}
        </ul>
        {ready?.degraded_mode.length ? (
          <p className="mt-4 text-sm text-warning">
            Degraded: {ready.degraded_mode.map(humanizeEnum).join(" · ")}
          </p>
        ) : null}
      </Drawer>
      <ExchangeInspector
        item={inspect}
        open={Boolean(inspect)}
        onClose={() => setInspect(null)}
      />
    </div>
  );
}
