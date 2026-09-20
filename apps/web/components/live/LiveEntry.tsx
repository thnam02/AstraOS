"use client";

import Link from "next/link";
import { ArrowRight, Headphones } from "@phosphor-icons/react";
import { useState } from "react";

import { LiveStatus } from "@/components/astra";
import { ErrorState } from "@/components/shared/EmptyState";
import { DecisionWorkflow } from "@/components/live/DecisionWorkflow";
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
    <div className="flex min-h-[calc(100dvh-6rem)] flex-col gap-8">
      <div className="grid flex-1 items-center gap-8 py-4 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-12 lg:py-6">
        <header className="space-y-5">
          <LiveStatus />
          <h1 className="max-w-2xl text-3xl font-semibold leading-[1.12] tracking-tight sm:text-4xl xl:text-5xl">
            How AstraOS handles one autonomous buyer-agent request
          </h1>
          <p className="max-w-xl text-base leading-7 text-muted">
            LIVE is the merchant operator view of a machine commerce decision.
            Production traffic arrives through the Agent API.
          </p>
          <p className="text-sm text-muted">
            <Link
              href="/integrations"
              className="underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
            >
              Connect buyer agents → Integrations
            </Link>
          </p>
        </header>

        <section className="border border-line bg-surface">
          <div className="border-b border-line px-6 py-4">
            <p className="eyebrow">Incoming buyer-agent request</p>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
              <span>
                Source <span className="text-ink">Operator test</span>
              </span>
              <span>
                Protocol <span className="text-ink">Agent API equivalent</span>
              </span>
              <span>
                Status <span className="text-ink">Compose</span>
              </span>
            </div>
          </div>

          <div className="border-b border-line px-6 py-4">
            <div className="inline-flex items-center gap-2 border border-line bg-canvas px-3 py-2">
              <Headphones size={16} weight="regular" aria-hidden />
              <div>
                <p className="text-sm font-medium">Headphones</p>
                <p className="type-small text-muted">
                  Demo catalogue is headphones only
                </p>
              </div>
            </div>
            <p className="mt-2 type-small text-muted">
              You can edit or replace this request — the sample prompt is not
              required. Ask anything about headphones.
            </p>
          </div>

          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (canRun) onRun();
            }}
          >
            <label className="block px-6 pt-5">
              <span className="sr-only">Headphones buyer-agent request</span>
              <Textarea
                value={text}
                onChange={(event) => onText(event.target.value)}
                rows={7}
                placeholder={HERO_INTENT}
                className="min-h-[14rem] resize-y rounded-[var(--radius-control)] border-line bg-canvas p-4 text-base leading-7 shadow-none md:text-lg"
              />
            </label>
            <div className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
              <button
                type="button"
                className="btn-quiet text-left"
                aria-expanded={showInspector}
                onClick={() => setShowInspector((current) => !current)}
              >
                {showInspector ? "Hide request options" : "Request options"}
              </button>
              <Button
                type="submit"
                size="lg"
                disabled={!canRun}
                className="h-12 rounded-[var(--radius-control)] px-6 text-base"
              >
                Process request
                <ArrowRight size={16} weight="bold" aria-hidden />
              </Button>
            </div>
            {showInspector ? (
              <div className="border-t border-line px-6 py-4">
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
      </div>
      <DecisionWorkflow active="understand" flags={IDLE_FLAGS} preview />
    </div>
  );
}
