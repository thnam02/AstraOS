"use client";

import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/shared/StatusBadge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getReady } from "@/lib/api";
import type { ConnectionStatus } from "@/types";

export function SystemHealth({
  timing,
}: {
  timing?: { total_ms?: number; intent_parse_ms?: number; qualification_ms?: number };
}) {
  const [status, setStatus] = useState<ConnectionStatus>("loading");
  const [degraded, setDegraded] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    getReady()
      .then((payload) => {
        if (cancelled) return;
        setDegraded(payload.degraded_mode ?? []);
        setStatus(payload.status === "not_ready" ? "unavailable" : "connected");
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("unavailable");
          setDegraded([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const label =
    status === "connected"
      ? degraded.length
        ? "Degraded"
        : "System"
      : status === "unavailable"
        ? "Offline"
        : "System";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="btn-quiet focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink">
        {label}
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-72 space-y-3 rounded-[6px] border-line p-3 shadow-none"
      >
        <div>
          <p className="eyebrow mb-2">API</p>
          <StatusBadge status={status} />
        </div>
        {degraded.length ? (
          <p className="text-xs leading-5 text-muted">
            Degraded: {degraded.join(", ").replaceAll("_", " ")}
          </p>
        ) : null}
        {timing?.total_ms != null ? (
          <p className="text-xs text-muted">
            {timing.total_ms.toFixed(0)} ms
            {timing.intent_parse_ms != null
              ? ` · parse ${timing.intent_parse_ms.toFixed(0)}`
              : ""}
            {timing.qualification_ms != null
              ? ` · qualify ${timing.qualification_ms.toFixed(0)}`
              : ""}
          </p>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
