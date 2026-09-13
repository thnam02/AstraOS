"use client";

import Link from "next/link";
import {
  AirplaneTilt,
  ArrowRight,
  Plus,
  ShieldCheck,
  Wallet,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { useState } from "react";

import { LiveStatus } from "@/components/astra";
import { ErrorState } from "@/components/shared/EmptyState";
import { ProcessRail } from "@/components/live/ProcessRail";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SCENARIOS } from "@/lib/decisionNarrative";
import { cn } from "@/lib/utils";
import type { BuyerProfile } from "@/types";

const ICONS: Record<string, Icon> = {
  urgent: AirplaneTilt,
  budget: Wallet,
  assurance: ShieldCheck,
  custom: Plus,
};

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
  onScenario,
  onCustom,
}: {
  text: string;
  parserMode: "rule_based" | "llm";
  error: string | null;
  onText: (value: string) => void;
  onParser: (mode: "rule_based" | "llm") => void;
  onRun: () => void;
  onScenario: (intent: string, profile: BuyerProfile) => void;
  onCustom: () => void;
}) {
  const matched = SCENARIOS.find((item) => item.intent === text);
  const selected = matched?.id ?? "custom";
  const canRun = Boolean(text.trim());
  const [showInspector, setShowInspector] = useState(false);

  return (
    <div className="mx-auto w-full max-w-3xl space-y-8 py-8">
      <header className="space-y-3">
        <LiveStatus />
        <h1 className="type-display max-w-2xl">
          How AstraOS handles one autonomous buyer-agent request
        </h1>
        <p className="max-w-xl text-[15px] leading-6 text-muted">
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
        <div className="border-b border-line px-4 py-3">
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
          <p className="mt-2 type-small text-muted">
            This form creates a test request so you can inspect the decision
            pipeline. It is not production buyer-agent traffic.
          </p>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (canRun) onRun();
          }}
        >
          <label className="block px-4 pt-3">
            <span className="sr-only">Buyer agent request text</span>
            <Textarea
              value={text}
              onChange={(event) => onText(event.target.value)}
              rows={5}
              placeholder="Paste or compose the buyer-agent request…"
              className="min-h-[8rem] resize-y rounded-[var(--radius-control)] border-line bg-canvas text-[15px] leading-6 shadow-none"
            />
          </label>
          <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
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
              className="h-10 rounded-[var(--radius-control)] px-5"
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

      <section>
        <p className="eyebrow">Test scenarios</p>
        <p className="mt-1 type-small text-muted">
          Synthetic intents for development and inspection — not live traffic.
        </p>
        <div
          className="mt-3 flex flex-wrap gap-2"
          role="group"
          aria-label="Test scenarios"
        >
          {SCENARIOS.map((item) => {
            const Icon = ICONS[item.id];
            const active = selected === item.id;
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={active}
                onClick={() => onScenario(item.intent, item.profile)}
                className={cn(
                  "inline-flex cursor-pointer items-center gap-2 border px-3 py-2 text-sm motion-safe:transition-colors",
                  "rounded-[var(--radius-control)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                  active
                    ? "border-ink bg-ink text-surface"
                    : "border-line bg-surface text-ink hover:border-ink",
                )}
              >
                {Icon ? <Icon size={16} weight="regular" aria-hidden /> : null}
                {item.label}
              </button>
            );
          })}
          <button
            type="button"
            aria-pressed={selected === "custom"}
            onClick={onCustom}
            className={cn(
              "inline-flex cursor-pointer items-center gap-2 border px-3 py-2 text-sm motion-safe:transition-colors",
              "rounded-[var(--radius-control)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
              selected === "custom"
                ? "border-ink bg-ink text-surface"
                : "border-line bg-surface text-ink hover:border-ink",
            )}
          >
            <Plus size={16} weight="regular" aria-hidden />
            Manual request
          </button>
        </div>
      </section>

      <section>
        <p className="eyebrow">Decision pipeline</p>
        <p className="mt-1 type-small text-muted">
          Understand → Qualify → Match → Construct → Optimise → Negotiate →
          Transact
        </p>
        <div className="mt-2 overflow-x-auto pb-1">
          <ProcessRail
            active="understand"
            flags={IDLE_FLAGS}
            interactive={false}
            preview
          />
        </div>
      </section>
    </div>
  );
}
