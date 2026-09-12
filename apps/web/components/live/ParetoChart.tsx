"use client";

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { formatAudCents } from "@/lib/money";
import type { PlotPoint } from "@/types";

function dollars(cents: number): number {
  return Math.round(cents) / 100;
}

function TooltipBody({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: PlotPoint }[];
}) {
  if (!active || !payload?.[0]) return null;
  const point = payload[0].payload;
  return (
    <div className="border border-line bg-surface px-3 py-2 text-xs shadow-panel">
      <p className="font-medium">{point.product_name}</p>
      <p className="font-mono text-muted">{point.sku}</p>
      <p>Price {formatAudCents(point.total_price_cents)}</p>
      <p>
        {point.delivery_code} · {point.warranty_code} · {point.bundle_code ?? "NONE"}
      </p>
      <p>Simulated utility {point.buyer_utility.toFixed(3)}</p>
      <p>Merchant contribution {formatAudCents(point.contribution_margin_cents)}</p>
      <p>Intervention {formatAudCents(point.intervention_cost_cents)}</p>
    </div>
  );
}

export function ParetoChart({ points }: { points: PlotPoint[] }) {
  const dominated = points.filter((item) => !item.is_pareto_efficient);
  const frontier = points.filter(
    (item) => item.is_pareto_efficient && !item.is_recommended,
  );
  const recommended = points.filter((item) => item.is_recommended);
  const selected = recommended[0];

  return (
    <div>
      <div className="h-[320px] w-full" role="img" aria-label="Pareto scatter of merchant contribution versus simulated buyer utility">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="#dddad2" />
            <XAxis
              type="number"
              dataKey="x"
              name="Contribution"
              tick={{ fontSize: 11, fill: "#5c5a54" }}
              tickFormatter={(value: number) => `$${value}`}
              label={{
                value: "Merchant contribution (A$)",
                position: "insideBottom",
                offset: -2,
                fontSize: 11,
                fill: "#5c5a54",
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Utility"
              domain={[0, 1]}
              tick={{ fontSize: 11, fill: "#5c5a54" }}
              label={{
                value: "Simulated buyer utility",
                angle: -90,
                position: "insideLeft",
                fontSize: 11,
                fill: "#5c5a54",
              }}
            />
            <ZAxis type="number" dataKey="z" range={[20, 160]} />
            <Tooltip content={<TooltipBody />} />
            <Scatter
              name="Dominated"
              shape="circle"
              data={dominated.map((item) => ({
                ...item,
                x: dollars(item.contribution_margin_cents),
                y: item.buyer_utility,
                z: Math.max(item.intervention_cost_cents, 80),
              }))}
              fill="#c4c4be"
              fillOpacity={0.45}
            />
            <Scatter
              name="Pareto"
              shape="square"
              data={frontier.map((item) => ({
                ...item,
                x: dollars(item.contribution_margin_cents),
                y: item.buyer_utility,
                z: Math.max(item.intervention_cost_cents, 120),
              }))}
              fill="#141413"
            />
            <Scatter
              name="Recommended"
              shape="diamond"
              data={recommended.map((item) => ({
                ...item,
                x: dollars(item.contribution_margin_cents),
                y: item.buyer_utility,
                z: Math.max(item.intervention_cost_cents, 180),
              }))}
              fill="#1b7f4a"
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-3 flex flex-wrap gap-4 text-[11px] text-muted">
        <li>Circle · muted = dominated</li>
        <li>Square · black = Pareto-efficient</li>
        <li>Diamond · green = AstraOS response</li>
      </ul>
      {selected ? (
        <p className="mt-2 font-mono text-xs tabular-nums">
          Selected {selected.product_name} · {formatAudCents(selected.total_price_cents)} ·
          contribution {formatAudCents(selected.contribution_margin_cents)} ·
          utility {selected.buyer_utility.toFixed(3)}
        </p>
      ) : null}
      <p className="mt-1 text-[11px] text-muted">
        {frontier.length + recommended.length} Pareto points, {dominated.length}{" "}
        dominated shown. Values are from the optimisation run, not a mock series.
      </p>
    </div>
  );
}
