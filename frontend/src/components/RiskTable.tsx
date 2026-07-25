"use client";

import { ScoreResponse } from "@/lib/types";
import { RiskBadge } from "./RiskBadge";
import { StatBar } from "./StatBar";
import { Button } from "./ui/button";
import { motion } from "framer-motion";

interface RiskTableProps {
  data: ScoreResponse[];
  onViewDetails: (customer: ScoreResponse) => void;
}

export function RiskTable({ data, onViewDetails }: RiskTableProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground text-sm glass rounded-xl">
        No flagged customers found. Ask a question to begin an investigation.
      </div>
    );
  }

  // Sort by risk level (high > medium > low) and then by final score
  const sorted = [...data].sort((a, b) => {
    const riskWeight = { high: 3, medium: 2, low: 1 };
    if (riskWeight[a.risk_level] !== riskWeight[b.risk_level]) {
      return riskWeight[b.risk_level] - riskWeight[a.risk_level];
    }
    return b.final_score - a.final_score;
  });

  return (
    <div className="w-full overflow-hidden rounded-xl border border-white/5 bg-black/40 backdrop-blur-md">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-muted-foreground uppercase bg-white/5 border-b border-white/5">
            <tr>
              <th className="px-6 py-4 font-medium">Customer ID</th>
              <th className="px-6 py-4 font-medium">Risk Level</th>
              <th className="px-6 py-4 font-medium">Final Score</th>
              <th className="px-6 py-4 font-medium">Primary Reason</th>
              <th className="px-6 py-4 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item, index) => {
              const rule = item.triggered_rules?.[0]?.rule || "ML Anomaly";
              
              return (
                <motion.tr 
                  key={item.customer_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="border-b border-white/5 hover:bg-white/5 transition-colors group cursor-pointer"
                  onClick={() => onViewDetails(item)}
                >
                  <td className="px-6 py-4 font-mono">{item.customer_id}</td>
                  <td className="px-6 py-4">
                    <RiskBadge level={item.risk_level} />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3 w-32">
                      <span className="font-mono text-xs w-8">
                        {item.final_score.toFixed(2)}
                      </span>
                      <StatBar 
                        total={1.0} 
                        high={item.risk_level === 'high' ? item.final_score : 0} 
                        medium={item.risk_level === 'medium' ? item.final_score : 0}
                        low={item.risk_level === 'low' ? item.final_score : 0}
                        className="flex-1"
                      />
                    </div>
                  </td>
                  <td className="px-6 py-4 truncate max-w-[200px] text-muted-foreground">
                    {rule}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                      View Details
                    </Button>
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
