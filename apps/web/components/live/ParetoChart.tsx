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
    <div className="border border-line bg-surface px-3 py-2 text-xs">
      <p className="font-medium">{point.product_name}</p>
      <p className="text-muted">{point.sku}</p>
      <p>Price {formatAudCents(point.total_price_cents)}</p>
      <p>
        {point.delivery_code} · {point.warranty_code} · {point.bundle_code ?? "NONE"}
      </p>
      <p>Utility {point.buyer_utility.toFixed(3)}</p>
      <p>Contribution {formatAudCents(point.contribution_margin_cents)}</p>
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

  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
          <CartesianGrid stroke="#e4e4e0" />
          <XAxis
            type="number"
            dataKey="x"
            name="Contribution"
            tick={{ fontSize: 11, fill: "#6f6f69" }}
            tickFormatter={(value: number) => `$${value}`}
            label={{
              value: "Merchant contribution (A$)",
              position: "insideBottom",
              offset: -2,
              fontSize: 11,
              fill: "#6f6f69",
            }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Utility"
            domain={[0, 1]}
            tick={{ fontSize: 11, fill: "#6f6f69" }}
            label={{
              value: "Simulated buyer utility",
              angle: -90,
              position: "insideLeft",
              fontSize: 11,
              fill: "#6f6f69",
            }}
          />
          <ZAxis type="number" dataKey="z" range={[20, 160]} />
          <Tooltip content={<TooltipBody />} />
          <Scatter
            name="Dominated"
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
            data={frontier.map((item) => ({
              ...item,
              x: dollars(item.contribution_margin_cents),
              y: item.buyer_utility,
              z: Math.max(item.intervention_cost_cents, 120),
            }))}
            fill="#171717"
          />
          <Scatter
            name="Recommended"
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
  );
}
