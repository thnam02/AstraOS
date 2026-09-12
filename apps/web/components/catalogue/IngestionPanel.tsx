"use client";

import { useEffect, useState } from "react";

import { DataBadge } from "@/components/shared/DataBadge";
import {
  getMerchantDataStatus,
  importMerchantFeed,
  listIngestionRuns,
  validateMerchantFeed,
} from "@/lib/api";
import type {
  IngestionResultResponse,
  IngestionRunSummary,
  MerchantDataStatusResponse,
} from "@/types";

function bytesToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

export function IngestionPanel({ onImported }: { onImported?: () => void }) {
  const [status, setStatus] = useState<MerchantDataStatusResponse | null>(null);
  const [runs, setRuns] = useState<IngestionRunSummary[]>([]);
  const [preview, setPreview] = useState<IngestionResultResponse | null>(null);
  const [pending, setPending] = useState<{
    source_type: "json" | "csv";
    source_name: string;
    snapshot?: Record<string, unknown>;
    content_base64?: string;
  } | null>(null);
  const [busy, setBusy] = useState<"validate" | "apply" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openRun, setOpenRun] = useState<string | null>(null);

  const refresh = () => {
    Promise.all([getMerchantDataStatus(), listIngestionRuns()])
      .then(([nextStatus, listing]) => {
        setStatus(nextStatus);
        setRuns(listing.items);
      })
      .catch(() => {
        setError("Unable to load ingestion status.");
      });
  };

  useEffect(() => {
    refresh();
  }, []);

  async function onFile(file: File) {
    setError(null);
    setPreview(null);
    const name = file.name.toLowerCase();
    const source_type: "json" | "csv" =
      name.endsWith(".csv") || name.endsWith(".zip") ? "csv" : "json";
    try {
      if (source_type === "json") {
        const text = await file.text();
        const snapshot = JSON.parse(text) as Record<string, unknown>;
        setPending({ source_type, source_name: file.name, snapshot });
        setBusy("validate");
        const result = await validateMerchantFeed({
          source_type,
          source_name: file.name,
          snapshot,
        });
        setPreview(result);
      } else {
        const content_base64 = bytesToBase64(await file.arrayBuffer());
        setPending({ source_type, source_name: file.name, content_base64 });
        setBusy("validate");
        const result = await validateMerchantFeed({
          source_type,
          source_name: file.name,
          content_base64,
        });
        setPreview(result);
      }
    } catch {
      setError("The file could not be validated. Use a versioned JSON or CSV zip.");
    } finally {
      setBusy(null);
    }
  }

  async function applyImport() {
    if (!pending) return;
    setBusy("apply");
    setError(null);
    try {
      const result = await importMerchantFeed(pending);
      setPreview(result);
      refresh();
      onImported?.();
    } catch {
      setError("Import failed. Catalogue was not left half-applied if validation failed.");
    } finally {
      setBusy(null);
    }
  }

  const counts = preview?.counts;
  const selected = runs.find((run) => run.id === openRun) ?? null;

  return (
    <section className="space-y-4 border border-line bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] tracking-[0.12em] text-muted uppercase">
            Import data
          </p>
          <p className="mt-1 text-sm text-muted">
            JSON or CSV zip. Dry-run first. Decisioning uses the canonical model
            whether data came from the demo seed or an import.
          </p>
        </div>
        <DataBadge tone="neutral">{status?.data_mode ?? "…"}</DataBadge>
      </div>

      <label className="inline-flex cursor-pointer items-center border border-line px-3 py-2 text-sm">
        <input
          type="file"
          accept=".json,.csv,.zip"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void onFile(file);
          }}
        />
        Upload merchant feed
      </label>

      {busy ? (
        <p className="text-sm text-muted">
          {busy === "validate" ? "Validating…" : "Applying import…"}
        </p>
      ) : null}
      {error ? <p className="text-sm text-danger">{error}</p> : null}

      {preview ? (
        <div className="space-y-3 border-t border-line pt-3">
          <p className="text-[11px] tracking-[0.12em] text-muted uppercase">
            Validation summary
          </p>
          <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
            <Stat label="Products" value={counts?.products?.received} />
            <Stat label="Variants" value={counts?.variants?.received} />
            <Stat label="Inventory" value={counts?.inventory?.received} />
            <Stat label="Evidence" value={counts?.evidence?.received} />
            <Stat label="Would create" value={preview.records_created} />
            <Stat label="Would update" value={preview.records_updated} />
            <Stat label="Warnings" value={preview.warnings.length} />
            <Stat label="Errors" value={preview.errors.length} />
          </div>
          {preview.errors.length ? (
            <ul className="space-y-1 text-sm text-danger">
              {preview.errors.slice(0, 6).map((item) => (
                <li key={`${item.code}-${item.location}`}>
                  {item.message}
                </li>
              ))}
            </ul>
          ) : null}
          {preview.warnings.length ? (
            <ul className="space-y-1 text-xs text-muted">
              {preview.warnings.slice(0, 4).map((item) => (
                <li key={`${item.code}-${item.location}`}>{item.message}</li>
              ))}
            </ul>
          ) : null}
          {preview.dry_run && preview.errors.length === 0 ? (
            <button
              type="button"
              onClick={() => void applyImport()}
              className="border border-ink bg-ink px-3 py-2 text-sm text-canvas"
            >
              Apply import
            </button>
          ) : null}
          {!preview.dry_run ? (
            <p className="text-xs text-muted">
              Semantic documents changed {preview.semantic_documents_changed}.
              Embeddings refreshed {preview.embeddings_refreshed}.
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-2 border-t border-line pt-3">
        <p className="text-[11px] tracking-[0.12em] text-muted uppercase">
          Import runs
        </p>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-xs">
            <thead className="text-muted">
              <tr>
                <th className="py-1 pr-3 font-medium">Time</th>
                <th className="py-1 pr-3 font-medium">Source</th>
                <th className="py-1 pr-3 font-medium">Status</th>
                <th className="py-1 pr-3 font-medium">Created</th>
                <th className="py-1 pr-3 font-medium">Updated</th>
                <th className="py-1 pr-3 font-medium">Unchanged</th>
                <th className="py-1 pr-3 font-medium">Warn</th>
                <th className="py-1 pr-3 font-medium">Err</th>
                <th className="py-1 pr-3 font-medium">Index</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className="cursor-pointer border-t border-line"
                  onClick={() =>
                    setOpenRun((current) => (current === run.id ? null : run.id))
                  }
                >
                  <td className="py-1 pr-3 tabular-nums">
                    {new Date(run.started_at).toLocaleString()}
                  </td>
                  <td className="py-1 pr-3">{run.source_name}</td>
                  <td className="py-1 pr-3">{run.status}</td>
                  <td className="py-1 pr-3 tabular-nums">{run.records_created}</td>
                  <td className="py-1 pr-3 tabular-nums">{run.records_updated}</td>
                  <td className="py-1 pr-3 tabular-nums">{run.records_unchanged}</td>
                  <td className="py-1 pr-3 tabular-nums">{run.warning_count}</td>
                  <td className="py-1 pr-3 tabular-nums">{run.error_count}</td>
                  <td className="py-1 pr-3">{run.index_status ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {selected ? (
          <p className="text-xs text-muted">
            {selected.source_type} · {selected.snapshot_mode} · hash{" "}
            {selected.file_hash?.slice(0, 12) ?? "—"}
          </p>
        ) : null}
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value?: number }) {
  return (
    <div className="border border-line px-2 py-2">
      <p className="text-[10px] tracking-[0.08em] text-muted uppercase">{label}</p>
      <p className="text-sm font-medium tabular-nums">{value ?? "—"}</p>
    </div>
  );
}
