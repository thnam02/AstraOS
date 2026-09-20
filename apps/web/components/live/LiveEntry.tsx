"use client";

import Link from "next/link";
import { ArrowRight, Headphones } from "@phosphor-icons/react";
import { useState } from "react";

import { LiveStatus } from "@/components/astra";
import { ErrorState } from "@/components/shared/EmptyState";
import { ProcessRail } from "@/components/live/ProcessRail";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { HERO_INTENT } from "@/lib/intent";

const IDLE_FLAGS = {
  hasMatch: false,
  hasOffers: false,
  hasOpt: false,
  hasNego: false,
  hasTxn: false,
  txnFailed: false,
  txnComplete: false,
};

export function LiveEntry({
  text,
  parserMode,
  error,
  onText,
  onParser,
  onRun,
}: {
  text: string;
  parserMode: "rule_based" | "llm";
  error: string | null;
  onText: (value: string) => void;
  onParser: (mode: "rule_based" | "llm") => void;
  onRun: () => void;
}) {
  const canRun = Boolean(text.trim());
  const [showInspector, setShowInspector] = useState(false);

  return (
    <div className="w-full">
      <header className="space-y-2.5">
        <LiveStatus />
        <h1 className="live-entry-title max-w-3xl">
          How AstraOS handles one autonomous buyer-agent request
        </h1>
        <p className="live-entry-lede max-w-2xl">
          LIVE is the merchant operator view of a machine commerce decision.
          Production traffic arrives through the Agent API.{" "}
          <Link
            href="/integrations"
            className="text-ink underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
          >
            Connect buyer agents → Integrations
          </Link>
        </p>
      </header>

      <section className="mt-6 border border-line bg-surface">
        <div className="flex min-h-11 flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b border-line px-4 py-2.5 md:min-h-12">
          <p className="eyebrow text-[11px] tracking-[0.07em] md:text-xs">
            Incoming buyer-agent request
          </p>
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted md:text-[13px]">
            <span>
              Source <span className="font-medium text-ink">Operator test</span>
            </span>
            <span>
              Protocol{" "}
              <span className="font-medium text-ink">Agent API equivalent</span>
            </span>
            <span>
              Status <span className="font-medium text-ink">Compose</span>
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 border-b border-line px-4 py-3">
          <div className="inline-flex items-center gap-2.5 border border-line bg-canvas px-3 py-2">
            <Headphones size={18} weight="regular" aria-hidden />
            <div>
              <p className="text-[15px] font-medium leading-none">Headphones</p>
              <p className="mt-1 type-small text-muted">
                Demo catalogue · headphones only
              </p>
            </div>
          </div>
          <p className="min-w-0 flex-1 text-sm leading-5 text-muted">
            Edit or replace this sample — ask anything about headphones.
          </p>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (canRun) onRun();
          }}
        >
          <label className="block px-4 pt-3.5">
            <span className="sr-only">Headphones buyer-agent request</span>
            <Textarea
              value={text}
              onChange={(event) => onText(event.target.value)}
              rows={4}
              placeholder={HERO_INTENT}
              className="min-h-[7rem] resize-y rounded-[var(--radius-control)] border-line bg-canvas text-[15px] leading-6 shadow-none md:min-h-[7.5rem]"
            />
          </label>
          <div className="flex flex-col gap-3 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              className="btn-quiet text-left text-sm text-muted"
              aria-expanded={showInspector}
              onClick={() => setShowInspector((current) => !current)}
            >
              {showInspector ? "Hide request options" : "Request options"}
            </button>
            <Button
              type="submit"
              size="lg"
              disabled={!canRun}
              className="h-11 w-full rounded-[var(--radius-control)] px-5 sm:h-12 sm:w-[158px]"
            >
              Process request
              <ArrowRight size={16} weight="bold" aria-hidden />
            </Button>
          </div>
          {showInspector ? (
            <div className="border-t border-line px-4 py-3">
              <label className="flex flex-wrap items-center gap-2 text-xs text-muted">
                <span id="parser-label">Intent parser (technical)</span>
                <select
                  aria-labelledby="parser-label"
                  value={parserMode}
                  onChange={(event) =>
                    onParser(event.target.value as "rule_based" | "llm")
                  }
                  className="control px-2 py-1"
                >
                  <option value="llm">LLM</option>
                  <option value="rule_based">Rule-based</option>
                </select>
              </label>
            </div>
          ) : null}
          {error ? (
            <div className="px-4 pb-4">
              <ErrorState message={error} />
            </div>
          ) : null}
        </form>
      </section>

      <section className="mt-7">
        <p className="eyebrow text-[11px] tracking-[0.07em] md:text-xs">
          Decision pipeline
        </p>
        <div className="mt-3 w-full overflow-x-auto pb-0.5">
          <ProcessRail
            active="understand"
            flags={IDLE_FLAGS}
            interactive={false}
            preview
            spread
          />
        </div>
      </section>
    </div>
  );
}
