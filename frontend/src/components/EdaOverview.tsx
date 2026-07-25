"use client";

import { EdaResponse } from "@/lib/types";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { StatBar } from "./StatBar";

interface EdaOverviewProps {
  data: EdaResponse | null;
}

const COLORS = ['#22C55E', '#10b981', '#059669', '#047857', '#064e3b'];

export function EdaOverview({ data }: EdaOverviewProps) {
  if (!data) return null;

  // Fake some distribution curve data using the stats
  const distData = [
    { name: 'Min', value: 0 },
    { name: 'Mean', value: data.amount_distribution.mean },
    { name: 'Median', value: data.amount_distribution.median },
    { name: 'P95', value: data.amount_distribution.p95 },
    { name: 'P99', value: data.amount_distribution.p99 }
  ];

  const channelData = Object.entries(data.transactions_by_channel).map(([name, value]) => ({ name, value }));
  const typeData = Object.entries(data.transactions_by_type).map(([name, value]) => ({ name, value }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Amount Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={distData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22C55E" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#22C55E" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" stroke="#525252" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#525252" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `$${val}`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1A1F1D', border: '1px solid #2A2F2D', borderRadius: '8px' }}
                  itemStyle={{ color: '#22C55E', fontFamily: 'var(--font-mono)' }}
                />
                <Area type="monotone" dataKey="value" stroke="#22C55E" fillOpacity={1} fill="url(#colorValue)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Risk Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4">
              <StatBar 
                low={data.risk_level_breakdown.low} 
                medium={data.risk_level_breakdown.medium} 
                high={data.risk_level_breakdown.high} 
                className="h-4"
              />
              <div className="flex justify-between text-xs text-muted-foreground font-mono">
                <span className="text-risk-low">{data.risk_level_breakdown.low || 0} Low</span>
                <span className="text-risk-medium">{data.risk_level_breakdown.medium || 0} Med</span>
                <span className="text-risk-high">{data.risk_level_breakdown.high || 0} High</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="flex-1">
          <CardHeader>
            <CardTitle>Channel Volume</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center items-center">
            <div className="h-40 w-full relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={channelData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={60}
                    paddingAngle={5}
                    dataKey="value"
                    stroke="none"
                  >
                    {channelData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1A1F1D', border: '1px solid #2A2F2D', borderRadius: '8px' }}
                    itemStyle={{ color: '#ededed', fontFamily: 'var(--font-mono)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
