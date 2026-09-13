"use client";

import {
  AirplaneTilt,
  ArrowRight,
  Plus,
  ShieldCheck,
  Wallet,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";

import { LiveStatus } from "@/components/astra";
import { ErrorState } from "@/components/shared/EmptyState";
import { ProcessRail } from "@/components/live/ProcessRail";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { SCENARIOS } from "@/lib/decisionNarrative";
import { HERO_INTENT } from "@/lib/intent";
import { cn } from "@/lib/utils";
import type { BuyerProfile } from "@/types";

const ICONS: Record<string, Icon> = {
  urgent: AirplaneTilt,
  budget: Wallet,
  assurance: ShieldCheck,
  custom: Plus,
};

const EVALUATES = [
  "Buyer intent",
  "Budget",
  "Delivery urgency",
  "Product fit",
  "Merchant constraints",
  "Offer quality",
] as const;

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

  return (
    <div className="mx-auto w-full max-w-3xl space-y-8 py-8">
      <header className="space-y-3">
        <LiveStatus />
        <h1 className="type-display max-w-2xl">
          Merchant-side offer intelligence for autonomous buyers
        </h1>
        <p className="max-w-xl text-[15px] leading-6 text-muted">
          The unit of competition is the complete offer, not only the product
          or the price.
        </p>
      </header>

      <section>
        <p className="eyebrow">Quick scenarios</p>
        <div
          className="mt-3 flex flex-wrap gap-2"
          role="group"
          aria-label="Quick scenarios"
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
                  "rounded-[6px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
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
              "rounded-[6px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
              selected === "custom"
                ? "border-ink bg-ink text-surface"
                : "border-line bg-surface text-ink hover:border-ink",
            )}
          >
            <Plus size={16} weight="regular" aria-hidden />
            Custom request
          </button>
        </div>
      </section>

      <form
        className="border border-line bg-surface"
        onSubmit={(event) => {
          event.preventDefault();
          if (canRun) onRun();
        }}
      >
        <div className="border-b border-line px-4 py-3">
          <p className="eyebrow">Buyer request</p>
          <p className="mt-1 type-small text-muted">
            Tell AstraOS what the buyer needs
          </p>
        </div>
        <label className="block px-4 pt-3">
          <span className="sr-only">Buyer agent request</span>
          <Textarea
            value={text}
            onChange={(event) => onText(event.target.value)}
            rows={5}
            className="min-h-[8rem] resize-y rounded-[6px] border-line bg-canvas text-[15px] leading-6 shadow-none"
          />
        </label>
        <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <span className="type-small text-muted" id="parser-label">
              Parser
            </span>
            <Select
              value={parserMode}
              onValueChange={(value) =>
                onParser(value as "rule_based" | "llm")
              }
            >
              <SelectTrigger
                size="sm"
                aria-labelledby="parser-label"
                className="rounded-[6px] border-line bg-surface shadow-none"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="llm">LLM</SelectItem>
                <SelectItem value="rule_based">Rule-based</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button
            type="submit"
            size="lg"
            disabled={!canRun}
            className="h-10 rounded-[6px] px-5"
          >
            Analyse request
            <ArrowRight size={16} weight="bold" aria-hidden />
          </Button>
        </div>
        {error ? (
          <div className="px-4 pb-4">
            <ErrorState
              message={error}
            />
          </div>
        ) : null}
      </form>

      <section>
        <p className="eyebrow">Decision pipeline</p>
        <div className="mt-3 overflow-x-auto">
          <ProcessRail active="understand" flags={IDLE_FLAGS} interactive={false} />
        </div>
        <p className="mt-2 type-small text-muted">
          Understand is ready. Later stages stay inactive until AstraOS runs.
        </p>
      </section>

      <section>
        <p className="eyebrow">What AstraOS evaluates</p>
        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 type-small text-muted">
          {EVALUATES.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
