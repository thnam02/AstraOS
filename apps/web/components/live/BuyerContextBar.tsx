"use client";

import { useState } from "react";

import { buyerRequestHighlights } from "@/lib/intent";
import type { ShoppingIntent } from "@/types";

import { IntentPanel } from "./IntentPanel";
import { SystemHealth } from "./SystemHealth";

export function BuyerContextBar({
  intent,
  rawText,
  onEdit,
  onRerun,
  busy,
}: {
  intent: ShoppingIntent;
  rawText: string;
  onEdit: () => void;
  onRerun: () => void;
  busy: boolean;
}) {
  const highlights = buyerRequestHighlights(intent);
  const [open, setOpen] = useState(false);

  return (
    <section className="max-w-[1120px] border-b border-line pb-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <p className="text-sm leading-6">
          <span className="eyebrow mr-3 align-middle">Buyer agent</span>
          <span>{highlights.join(" · ")}</span>
        </p>
        <div className="flex shrink-0 items-center gap-3">
          <button type="button" className="btn-quiet" onClick={onEdit}>
            Edit request
          </button>
          <button
            type="button"
            className="btn-quiet"
            disabled={busy}
            onClick={onRerun}
          >
            {busy ? "Rerunning…" : "Rerun"}
          </button>
          <SystemHealth />
        </div>
      </div>
      <button
        type="button"
        className="btn-quiet mt-1"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {open ? "Hide interpreted intent" : "View interpreted intent"}
      </button>
      {open ? (
        <div className="mt-3 max-w-3xl space-y-4">
          <p className="text-sm leading-6 text-muted">“{rawText}”</p>
          <IntentPanel intent={intent} compact />
        </div>
      ) : null}
    </section>
  );
}
