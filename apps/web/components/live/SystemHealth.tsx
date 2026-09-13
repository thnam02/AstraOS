"use client";

import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/shared/StatusBadge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getReady } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ConnectionStatus } from "@/types";

export function SystemHealth() {
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

  const tone =
    status === "unavailable"
      ? "bg-danger"
      : status === "connected" && degraded.length
        ? "bg-warning"
        : status === "connected"
          ? "bg-success"
          : "bg-muted";
  const label =
    status === "unavailable"
      ? "System offline"
      : degraded.length
        ? "System degraded"
        : status === "connected"
          ? "System connected"
          : "Checking system";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={label}
        className="inline-flex h-7 w-7 cursor-pointer items-center justify-center rounded-[6px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <span className={cn("h-1.5 w-1.5 rounded-full", tone)} aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-72 space-y-3 rounded-[6px] border-line p-3 shadow-none"
      >
        <div>
          <p className="eyebrow mb-2">System status</p>
          <StatusBadge status={status} />
        </div>
        {degraded.length ? (
          <p className="text-xs leading-5 text-muted">
            {degraded.join(", ").replaceAll("_", " ")}
          </p>
        ) : (
          <p className="text-xs text-muted">No operational warnings.</p>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
