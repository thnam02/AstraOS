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

  return (
    <div className="space-y-8">
      <AstraSectionHeader
        eyebrow="Integrations"
        title="Connect autonomous buyer agents to AstraOS"
        description="Machine access to the merchant decision system. AstraOS answers through the public Agent API; MCP is an optional adapter over the same REST contract."
      />

      {error ? (
        <AstraErrorState
          title="Unable to load agent API status"
          message={error}
          next="Confirm the API is running, then retry."
        />
      ) : null}
      {error ? (
        <button type="button" className="btn-primary" onClick={load}>
          Retry
        </button>
      ) : null}

      <AstraPanel>
        <p className="eyebrow">Architecture</p>
        <p className="mt-2 font-mono text-sm leading-7 text-ink">
          BUYER AGENT
          <br />
          &nbsp;&nbsp;↓
          <br />
          AGENT API
          <br />
          &nbsp;&nbsp;↓
          <br />
          ASTRAOS
          <br />
          &nbsp;&nbsp;↓
          <br />
          Merchant Data + Merchant Rules
        </p>
        <p className="mt-3 type-small text-muted">
          Machine responses are grounded in merchant truth and policy authority.
        </p>
      </AstraPanel>

      <div className="grid gap-4 lg:grid-cols-2">
        <AstraPanel tone="primary">
          <p className="eyebrow">Agent API</p>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div>
              <dt className="text-muted">Status</dt>
              <dd className="mt-1">
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
                    {humanizeEnum(ready.status)}
                  </AstraStatusBadge>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Protocol</dt>
              <dd className="mt-1 font-medium">
                {capabilities?.protocol?.join(" · ") ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-muted">API version</dt>
              <dd className="mt-1 font-mono">{capabilities?.version ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted">Service</dt>
              <dd className="mt-1 font-mono text-xs">
                {capabilities?.service ?? "—"}
              </dd>
            </div>
          </dl>
          {capabilities?.disclaimer ? (
            <p className="mt-3 type-small text-muted">{capabilities.disclaimer}</p>
          ) : null}
          {!apiOnline && ready ? (
            <p className="mt-2 text-sm text-danger">
              Readiness reports {ready.status}. Agent traffic may be unreliable.
            </p>
          ) : null}
        </AstraPanel>

        <AstraPanel>
          <p className="eyebrow">MCP adapter</p>
          <div className="mt-3">
            <AstraStatusBadge tone={mcpAvailable ? "positive" : "warning"}>
              {mcpAvailable ? "Available" : "Not advertised"}
            </AstraStatusBadge>
          </div>
          <p className="mt-3 text-sm leading-6 text-muted">
            Allows compatible agent clients to access AstraOS through MCP while
            the adapter continues to use the public AstraOS REST interface. MCP
            is not the core backend.
          </p>
        </AstraPanel>
      </div>

      <AstraPanel>
        <p className="eyebrow">Capabilities</p>
        <p className="mt-1 type-small text-muted">
          From GET /api/v1/agent/capabilities — not a static catalogue.
        </p>
        {operations.length ? (
          <ul className="mt-4 divide-y divide-line border-t border-line">
            {operations.map((row) => (
              <li
                key={row.operation}
                className="flex flex-wrap items-baseline justify-between gap-2 py-2 text-sm"
              >
                <span className="text-xs tracking-[0.08em] text-muted">
                  {row.group.toUpperCase()}
                </span>
                <span className="font-medium">{row.label}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted">No capabilities loaded.</p>
        )}
        {capabilities?.supported?.length ? (
          <p className="mt-3 type-small text-muted">
            Supported: {capabilities.supported.join(" · ")}
          </p>
        ) : null}
        {capabilities?.not_supported?.length ? (
          <p className="mt-1 type-small text-muted">
            Not supported: {capabilities.not_supported.join(" · ")}
          </p>
        ) : null}
      </AstraPanel>

      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="eyebrow">Recent agent activity</p>
            <p className="mt-1 type-small text-muted">
              Real negotiation sessions from AstraOS. Empty until traffic or
              operator tests exist.
            </p>
          </div>
          <button type="button" className="btn-ghost" onClick={load}>
            Refresh
          </button>
        </div>

        {activityError ? (
          <AstraErrorState
            title="Activity unavailable"
            message={activityError}
            next="Agent API status above may still be valid. Retry after confirming the API includes /agent/activity."
          />
        ) : null}

        {!activityError && activity && activity.length === 0 ? (
          <AstraEmptyState
            title="No agent activity yet"
            body="No autonomous buyer requests have been received."
            action={
              <div className="flex flex-wrap gap-2">
                <Link href="/" className="btn-primary">
                  Create test request
                </Link>
                <a
                  href={openApiDocsUrl()}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-ghost"
                >
                  View API reference
                </a>
              </div>
            }
          />
        ) : null}

        {!activityError && activity && activity.length > 0 ? (
          <div className="overflow-x-auto border border-line bg-surface">
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-line bg-canvas text-left text-[11px] font-medium tracking-[0.06em] text-muted uppercase">
                  <th className="whitespace-nowrap px-3 py-2">When</th>
                  <th className="px-3 py-2">Event</th>
                  <th className="whitespace-nowrap px-3 py-2">Channel</th>
                  <th className="whitespace-nowrap px-3 py-2">Ref</th>
                  <th className="whitespace-nowrap px-3 py-2">Status</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right">Total</th>
                  <th className="w-px whitespace-nowrap px-3 py-2 text-right">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {activity.map((item) => {
                  const fullRef =
                    item.order_number ??
                    item.request_id ??
                    item.proposal_id ??
                    item.negotiation_session_id;
                  const shortRef = item.order_number
                    ? item.order_number
                    : fullRef.replace(/-/g, "").slice(0, 8);
                  const when = new Date(item.occurred_at);
                  return (
                    <tr
                      key={item.negotiation_session_id}
                      className="border-b border-line last:border-0 hover:bg-canvas/70"
                    >
                      <td className="whitespace-nowrap px-3 py-2 align-middle tabular-nums text-xs text-muted">
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
                      </td>
                      <td className="max-w-[18rem] px-3 py-2 align-middle">
                        <p className="truncate font-medium leading-5">
                          {activityKindLabel(item.kind)}
                        </p>
                        <p
                          className="truncate text-xs leading-4 text-muted"
                          title={item.intent_summary}
                        >
                          {item.intent_summary}
                        </p>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 align-middle text-xs">
                        {channelLabel(item.channel)}
                      </td>
                      <td
                        className="whitespace-nowrap px-3 py-2 align-middle font-mono text-xs tabular-nums text-muted"
                        title={fullRef}
                      >
                        {shortRef}
                      </td>
                      <td className="max-w-[8.5rem] px-3 py-2 align-middle text-xs">
                        <span className="line-clamp-1" title={humanizeEnum(item.status)}>
                          {humanizeEnum(item.status)}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 align-middle text-right font-mono text-xs tabular-nums">
                        {item.total_amount_cents != null
                          ? formatAudCents(item.total_amount_cents)
                          : "—"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 align-middle text-right">
                        <button
                          type="button"
                          className="btn-quiet"
                          onClick={() => setInspect(item)}
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <AstraPanel>
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <p className="eyebrow">API reference</p>
            <p className="mt-1 type-small text-muted">
              Concise public contract. Full schemas live in OpenAPI.
            </p>
          </div>
          <a
            href={openApiDocsUrl()}
            target="_blank"
            rel="noreferrer"
            className="btn-ghost"
          >
            Open API docs
          </a>
        </div>
        <ul className="mt-4 divide-y divide-line border-t border-line">
          {AGENT_API_REFERENCE.map((row) => (
            <li
              key={`${row.method}-${row.path}`}
              className="grid gap-1 py-2 text-sm md:grid-cols-[5rem_1fr_1fr] md:items-baseline md:gap-4"
            >
              <span className="font-mono text-xs font-semibold">{row.method}</span>
              <code className="font-mono text-xs">{row.path}</code>
              <span className="text-muted">{row.purpose}</span>
            </li>
          ))}
        </ul>
      </AstraPanel>

      <ExchangeInspector
        item={inspect}
        open={Boolean(inspect)}
        onClose={() => setInspect(null)}
      />
    </div>
  );
}
