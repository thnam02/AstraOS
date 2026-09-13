"use client";

import { useState } from "react";

import { QualificationResults } from "@/components/live/QualificationResults";
import { Drawer } from "@/components/shared/Drawer";
import { qualifyIntent } from "@/lib/api";
import type { QualifyResponse } from "@/types";

export function QualificationInspect({
  intentText,
  parserMode,
}: {
  intentText: string;
  parserMode: "rule_based" | "llm";
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState<QualifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function inspect() {
    setOpen(true);
    if (detail || busy) return;
    setBusy(true);
    setError(null);
    try {
      setDetail(await qualifyIntent(intentText, parserMode));
    } catch {
      setError("Could not load qualification detail.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button type="button" className="btn-quiet" onClick={() => void inspect()}>
        Inspect qualification
      </button>
      <Drawer open={open} title="Qualification" onClose={() => setOpen(false)}>
        {busy ? <p className="text-sm text-muted">Loading eligibility…</p> : null}
        {error ? <p className="text-sm text-danger">{error}</p> : null}
        {detail ? (
          <div className="space-y-6">
            <dl className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <dt className="type-small text-muted">Eligible</dt>
                <dd className="mt-1 font-mono tabular-nums">
                  {detail.eligible_products.length}
                </dd>
              </div>
              <div>
                <dt className="type-small text-muted">Violated</dt>
                <dd className="mt-1 font-mono tabular-nums">
                  {detail.rejected_products.length}
                </dd>
              </div>
              <div>
                <dt className="type-small text-muted">Unknown</dt>
                <dd className="mt-1 font-mono tabular-nums">
                  {detail.uncertain_products.length}
                </dd>
              </div>
            </dl>
            <QualificationResults detail={detail} />
          </div>
        ) : null}
      </Drawer>
    </>
  );
}
