"use client";

import { useEffect, useState } from "react";

import { getMerchantPolicy, updateMerchantPolicy } from "@/lib/api";
import { formatRate } from "@/lib/money";
import type { MerchantPolicyResponse } from "@/types";

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
    getMerchantPolicy()
      .then((data) => {
        setPolicy(data);
        setMargin(String(Math.round(data.minimum_margin_rate * 100)));
        setDiscount(String(Math.round(data.maximum_discount_rate * 100)));
        setDelivery(data.delivery_subsidy_enabled);
        setWarranty(data.warranty_upgrade_enabled);
        setBundles(data.bundle_enabled);
        setReturns(data.flexible_returns_enabled);
      })
      .catch(() => {
        setError("Unable to load merchant policy.");
      });
  }, [open]);

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

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button
        type="button"
        className="absolute inset-0 bg-ink/20"
        aria-label="Close merchant rules"
        onClick={onClose}
      />
      <aside className="relative z-50 flex h-full w-full max-w-md flex-col border-l border-line bg-surface">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <p className="text-xs tracking-[0.14em] text-muted">MERCHANT</p>
            <h2 className="text-base font-semibold text-ink">Rules</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-muted hover:text-ink"
          >
            Close
          </button>
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <p className="text-sm leading-6 text-muted">
            Changing these rules is applied on the next optimisation run.
            The LLM does not override merchant policy.
          </p>
          {policy ? (
            <p className="text-xs text-muted">
              Active: {policy.name}. Current floor {formatRate(policy.minimum_margin_rate)},
              max discount {formatRate(policy.maximum_discount_rate)}.
            </p>
          ) : null}
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
          <div className="divide-y divide-line border-y border-line">
            <Toggle label="Delivery subsidy" checked={delivery} onChange={setDelivery} />
            <Toggle label="Warranty upgrades" checked={warranty} onChange={setWarranty} />
            <Toggle label="Bundles" checked={bundles} onChange={setBundles} />
            <Toggle label="Flexible returns" checked={returns} onChange={setReturns} />
          </div>
          {error ? <p className="text-sm text-danger">{error}</p> : null}
          {status === "saved" ? (
            <p className="text-sm text-success">Policy saved.</p>
          ) : null}
        </div>
        <div className="border-t border-line px-5 py-4">
          <button
            type="button"
            onClick={onSave}
            disabled={status === "saving"}
            className="w-full rounded-[6px] bg-ink px-3 py-2 text-sm font-medium text-surface disabled:opacity-60"
          >
            {status === "saving" ? "Saving…" : "Save rules"}
          </button>
        </div>
      </aside>
    </div>
  );
}
