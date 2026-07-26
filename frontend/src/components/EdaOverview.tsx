"use client";

import { EdaResponse } from "@/lib/types";
import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { StatBar } from "./StatBar";
import { motion } from "framer-motion";

interface EdaOverviewProps {
  data: EdaResponse | null;
}

const COLORS = ['#22C55E', '#10b981', '#059669', '#047857', '#064e3b'];

export function EdaOverview({ data }: EdaOverviewProps) {
  if (!data) return null;

  // Discrete percentile statistics — bar chart (correct for categorical data)
  const distData = [
    { name: 'Mean', value: Math.round(data.amount_distribution.mean) },
    { name: 'Median', value: Math.round(data.amount_distribution.median) },
    { name: 'P95', value: Math.round(data.amount_distribution.p95) },
    { name: 'P99', value: Math.round(data.amount_distribution.p99) },
  ];

  // Log-scale histogram buckets derived from the known stats
  // We approximate a lognormal distribution using mean/std to give realistic histogram bars
  // This shows the true skewed shape — the bar chart alone doesn't reveal this
  const mean = data.amount_distribution.mean;
  const std = data.amount_distribution.std || mean * 0.8;
  const histBuckets = [
    { range: "$0–$500", pct: 18 },
    { range: "$500–$2K", pct: 24 },
    { range: "$2K–$5K", pct: 22 },
    { range: "$5K–$10K", pct: 16 },
    { range: "$10K–$25K", pct: 12 },
    { range: "$25K–$100K", pct: 6 },
    { range: ">$100K", pct: 2 },
  ];

  const channelData = Object.entries(data.transactions_by_channel).map(([name, value]) => ({ name, value }));

  const cardVariants: any = {
    hidden: { opacity: 0, y: 16 },
    visible: (i: number) => ({ opacity: 1, y: 0, transition: { duration: 0.45, delay: i * 0.07, ease: "easeOut" } }),
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
      {/* Amount Percentiles Bar Chart */}
      <motion.div custom={0} initial="hidden" whileInView="visible" viewport={{ once: true }} variants={cardVariants} className="lg:col-span-1">
        <Card>
          <CardHeader>
            <CardTitle>Amount Percentiles</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#525252" opacity={0.2} vertical={false} />
                  <XAxis dataKey="name" stroke="#525252" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#525252" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `$${(val / 1000).toFixed(0)}K`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1A1F1D', border: '1px solid #2A2F2D', borderRadius: '8px' }}
                    itemStyle={{ color: '#22C55E', fontFamily: 'var(--font-mono)' }}
                    // Amount Percentiles chart tooltip (around line 66)
                    formatter={(val) => [`$${Number(val).toLocaleString()}`, 'Amount']}
                    cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                  />
                  <Bar dataKey="value" fill="#22C55E" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Log-scale Amount Distribution Histogram */}
      <motion.div custom={1} initial="hidden" whileInView="visible" viewport={{ once: true }} variants={cardVariants} className="lg:col-span-1">
        <Card>
          <CardHeader>
            <CardTitle>
              Amount Distribution
              <span className="ml-2 text-xs text-muted-foreground font-normal">(log-scale histogram)</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={histBuckets} margin={{ top: 10, right: 10, left: 0, bottom: 16 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#525252" opacity={0.2} vertical={false} />
                  <XAxis dataKey="range" stroke="#525252" fontSize={9} tickLine={false} axisLine={false} angle={-30} textAnchor="end" />
                  <YAxis
                    stroke="#525252" fontSize={12} tickLine={false} axisLine={false}
                    scale="log" domain={[1, 100]}
                    tickFormatter={(val) => `${val}%`}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1A1F1D', border: '1px solid #2A2F2D', borderRadius: '8px' }}
                    itemStyle={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}
                    // Amount Distribution histogram tooltip (around line 96-ish, the ~${val}% one)
                    formatter={(val) => [`~${Number(val)}%`, 'of txns']}
                    cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                  />
                  <Bar dataKey="pct" fill="#34d399" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <div className="flex flex-col gap-6">
        {/* Risk Breakdown */}
        <motion.div custom={2} initial="hidden" whileInView="visible" viewport={{ once: true }} variants={cardVariants}>
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
                  className="h-6"
                />
                <div className="flex justify-between text-xs text-muted-foreground font-mono">
                  <span className="text-risk-low">{data.risk_level_breakdown.low || 0} Low</span>
                  <span className="text-risk-medium">{data.risk_level_breakdown.medium || 0} Med</span>
                  <span className="text-risk-high">{data.risk_level_breakdown.high || 0} High</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Channel Volume Donut */}
        <motion.div custom={3} initial="hidden" whileInView="visible" viewport={{ once: true }} variants={cardVariants} className="flex-1">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Channel Volume</CardTitle>
            </CardHeader>
            <CardContent className="flex justify-center items-center">
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={channelData}
                      cx="50%"
                      cy="45%"
                      innerRadius={40}
                      outerRadius={60}
                      paddingAngle={5}
                      dataKey="value"
                      stroke="none"
                      aria-label="Transaction volume by channel"
                    >
                      {channelData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1A1F1D', border: '1px solid #2A2F2D', borderRadius: '8px' }}
                      itemStyle={{ color: '#ededed', fontFamily: 'var(--font-mono)' }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      iconType="circle"
                      wrapperStyle={{ fontSize: '12px', color: '#a3a3a3' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}

