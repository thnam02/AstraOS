"use client";

import { useEffect, useState } from "react";

import { getReady } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import type { ConnectionStatus } from "@/types";

export function ApiStatus() {
  const [status, setStatus] = useState<ConnectionStatus>("loading");
  const [degraded, setDegraded] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    getReady()
      .then((payload) => {
        if (cancelled) return;
        setDegraded(payload.degraded_mode ?? []);
        if (payload.status === "not_ready") {
          setStatus("unavailable");
        } else {
          setStatus("connected");
        }
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

  return (
    <section className="panel max-w-xs p-4">
      <p className="eyebrow mb-3">API status</p>
      <StatusBadge status={status} />
      {degraded.length ? (
        <p className="mt-2 text-xs leading-5 text-muted">
          Degraded: {degraded.join(", ").replaceAll("_", " ")}
        </p>
      ) : null}
    </section>
  );
}
