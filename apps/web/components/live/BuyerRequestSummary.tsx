"use client";

import { buyerRequestHighlights } from "@/lib/intent";
import type { ShoppingIntent } from "@/types";

import { IntentPanel } from "./IntentPanel";

export function BuyerRequestSummary({
  intent,
  rawText,
}: {
  intent: ShoppingIntent;
  rawText: string;
}) {
  const highlights = buyerRequestHighlights(intent);

  return (
    <section>
      <p className="eyebrow">Buyer request</p>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[15px] leading-6">
        {highlights.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <details className="mt-3 group">
        <summary className="btn-quiet cursor-pointer list-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink [&::-webkit-details-marker]:hidden">
          <span className="group-open:hidden">View interpreted intent</span>
          <span className="hidden group-open:inline">Hide interpreted intent</span>
        </summary>
        <div className="mt-4 max-w-3xl space-y-4">
          <p className="text-sm leading-6 text-muted">“{rawText}”</p>
          <IntentPanel intent={intent} />
        </div>
      </details>
    </section>
  );
}
