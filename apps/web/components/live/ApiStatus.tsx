"use client";

import { useEffect, useState } from "react";

import { getReady } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import type { ConnectionStatus } from "@/types";

export function ApiStatus() {
  const [status, setStatus] = useState<ConnectionStatus>("loading");

  useEffect(() => {
    let cancelled = false;

    getReady()
      .then((payload) => {
        if (!cancelled) {
          setStatus(
            payload.status === "not_ready" ? "unavailable" : "connected",
          );
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("unavailable");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="w-full max-w-xs rounded-[6px] border border-line bg-surface p-4">
      <p className="mb-3 text-xs font-medium tracking-[0.14em] text-muted">
        API STATUS
      </p>
      <StatusBadge status={status} />
    </section>
  );
}
