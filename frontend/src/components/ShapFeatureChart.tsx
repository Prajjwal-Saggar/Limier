"use client";

import { TopFeature } from "@/lib/types";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface ShapFeatureChartProps {
  features: TopFeature[];
}

export function ShapFeatureChart({ features }: ShapFeatureChartProps) {
  if (!features || features.length === 0) return null;

  // Recharts needs positive values for bars usually, so we'll take absolute magnitude for width 
  // but color by direction (red = pushes risk up, green = pushes risk down)
  const chartData = features.slice(0, 10).map(f => ({
    name: f.feature,
    value: f.value,
    shap: f.shap_contribution || 0,
    magnitude: Math.abs(f.shap_contribution || 0),
    isPositive: (f.shap_contribution || 0) > 0
  })).sort((a, b) => b.magnitude - a.magnitude);

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <XAxis type="number" hide />
          <YAxis 
            dataKey="name" 
            type="category" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#a3a3a3', fontSize: 12 }} 
            width={120}
          />
          <Tooltip 
            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
            contentStyle={{ backgroundColor: '#1A1F1D', border: '1px solid #2A2F2D', borderRadius: '8px' }}
            itemStyle={{ color: '#ededed', fontFamily: 'var(--font-mono)' }}
            formatter={(value: any, name: any, props: any) => {
              return [
                <span key="1" className="font-mono">
                  Val: {props.payload.value?.toFixed(2)} (SHAP: {props.payload.shap?.toFixed(4)})
                </span>, 
                "Contribution"
              ];
            }}
          />
          <Bar dataKey="magnitude" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.isPositive ? '#EF4444' : '#22C55E'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
