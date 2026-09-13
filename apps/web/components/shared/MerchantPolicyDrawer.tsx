"use client";

import { useEffect, useState } from "react";

import { AstraInspector, AstraStageHeader } from "@/components/astra";
import {
  getMerchantObjective,
  getMerchantPolicy,
  updateMerchantObjective,
  updateMerchantPolicy,
} from "@/lib/api";
import { formatRate } from "@/lib/money";
import type {
  MerchantObjectiveMode,
  MerchantObjectiveResponse,
  MerchantPolicyResponse,
} from "@/types";

const OBJECTIVE_MODES: MerchantObjectiveMode[] = [
  "GROWTH",
  "BALANCED",
  "MARGIN",
];

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 py-2">
      <span className="text-sm text-ink">{label}</span>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full border ${
          checked ? "border-ink bg-ink" : "border-line bg-canvas"
        }`}
        aria-pressed={checked}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-surface transition-transform ${
            checked ? "left-4" : "left-0.5"
          }`}
        />
      </button>
    </label>
  );
}

export function MerchantPolicyDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [policy, setPolicy] = useState<MerchantPolicyResponse | null>(null);
  const [objective, setObjective] = useState<MerchantObjectiveResponse | null>(
    null,
  );
  const [margin, setMargin] = useState("15");
  const [discount, setDiscount] = useState("10");
  const [delivery, setDelivery] = useState(true);
  const [warranty, setWarranty] = useState(true);
  const [bundles, setBundles] = useState(true);
  const [returns, setReturns] = useState(true);
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">(
    "idle",
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    setStatus("idle");
    setError(null);
    Promise.all([getMerchantPolicy(), getMerchantObjective()])
      .then(([data, currentObjective]) => {
        setPolicy(data);
        setObjective(currentObjective);
        setMargin(String(Math.round(data.minimum_margin_rate * 100)));
        setDiscount(String(Math.round(data.maximum_discount_rate * 100)));
        setDelivery(data.delivery_subsidy_enabled);
        setWarranty(data.warranty_upgrade_enabled);
        setBundles(data.bundle_enabled);
        setReturns(data.flexible_returns_enabled);
      })
      .catch(() => {
        setError("Unable to load merchant rules.");
      });
  }, [open]);

  async function onObjective(mode: MerchantObjectiveMode) {
    setStatus("saving");
    setError(null);
    try {
      const updated = await updateMerchantObjective({ mode });
      setObjective(updated);
      setStatus("saved");
      window.dispatchEvent(new CustomEvent("astraos:objective-changed"));
    } catch {
      setStatus("error");
      setError("Objective update failed.");
    }
  }

  async function onSave() {
    setStatus("saving");
    setError(null);
    try {
      const updated = await updateMerchantPolicy({
        minimum_margin_rate: Number(margin) / 100,
        maximum_discount_rate: Number(discount) / 100,
        delivery_subsidy_enabled: delivery,
        warranty_upgrade_enabled: warranty,
        bundle_enabled: bundles,
        flexible_returns_enabled: returns,
      });
      setPolicy(updated);
      setStatus("saved");
      window.dispatchEvent(new CustomEvent("astraos:policy-changed"));
    } catch {
      setStatus("error");
      setError("Policy update failed. Check the values and try again.");
    }
  }

  return (
    <AstraInspector open={open} title="Merchant rules" onClose={onClose}>
        <div className="space-y-5">
          <AstraStageHeader
            eyebrow="Merchant"
            title="Commercial boundaries"
            description="Guardrails define what is allowed. The commercial objective chooses among policy-safe Pareto offers."
          />
          {objective ? (
            <div className="space-y-3 border border-line px-3 py-3">
              <div>
                <p className="text-xs tracking-[0.14em] text-muted">
                  COMMERCIAL OBJECTIVE
                </p>
                <p className="mt-1 text-sm text-ink">
                  Current: {objective.label}
                </p>
                <p className="text-xs text-muted">{objective.blurb}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {OBJECTIVE_MODES.map((mode) => {
                  const preset = objective.presets[mode];
                  const active = objective.mode === mode;
                  return (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => onObjective(mode)}
                      className={`px-2.5 py-1 text-xs ${
                        active
                          ? "bg-ink text-surface"
                          : "border border-line text-ink hover:bg-canvas"
                      }`}
                    >
                      {preset?.label ?? mode}
                    </button>
                  );
                })}
              </div>
              <dl className="space-y-1 text-xs">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Buyer fit</dt>
                  <dd className="tabular-nums">
                    {Math.round(objective.buyer_weight * 100)}%
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Merchant contribution</dt>
                  <dd className="tabular-nums">
                    {Math.round(objective.merchant_weight * 100)}%
                  </dd>
                </div>
              </dl>
            </div>
          ) : null}
          {policy ? (
            <p className="text-xs text-muted">
              Active: {policy.name}. Current floor {formatRate(policy.minimum_margin_rate)},
              max discount {formatRate(policy.maximum_discount_rate)}.
            </p>
          ) : null}
          <p className="eyebrow">Economics</p>
          <label className="block space-y-1.5">
            <span className="text-xs font-medium text-muted">Minimum margin %</span>
            <input
              type="number"
              min={0}
              max={99}
              value={margin}
              onChange={(event) => setMargin(event.target.value)}
              className="w-full rounded-[6px] border border-line bg-canvas px-3 py-2 text-sm text-ink"
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-xs font-medium text-muted">Maximum discount %</span>
            <input
              type="number"
              min={0}
              max={100}
              value={discount}
              onChange={(event) => setDiscount(event.target.value)}
              className="w-full rounded-[6px] border border-line bg-canvas px-3 py-2 text-sm text-ink"
            />
          </label>
          <p className="eyebrow">Fulfilment & commercial options</p>
          <div className="divide-y divide-line border-y border-line">
            <Toggle label="Same-day / delivery subsidy" checked={delivery} onChange={setDelivery} />
            <Toggle label="Warranty upgrades" checked={warranty} onChange={setWarranty} />
            <Toggle label="Bundles" checked={bundles} onChange={setBundles} />
            <Toggle label="Flexible returns" checked={returns} onChange={setReturns} />
          </div>
          {error ? <p className="text-sm text-danger">{error}</p> : null}
          {status === "saved" ? (
            <p className="text-sm text-success">Policy saved.</p>
          ) : null}
          <div className="border-t border-line pt-4">
            <button
              type="button"
              onClick={onSave}
              disabled={status === "saving"}
              className="btn-primary w-full"
            >
              {status === "saving" ? "Saving…" : "Save rules"}
            </button>
          </div>
        </div>
    </AstraInspector>
  );
}
