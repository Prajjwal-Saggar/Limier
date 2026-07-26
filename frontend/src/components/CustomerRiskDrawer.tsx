"use client";

import { ScoreResponse } from "@/lib/types";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "./ui/sheet";
import { RiskBadge } from "./RiskBadge";
import { ShapFeatureChart } from "./ShapFeatureChart";

interface CustomerRiskDrawerProps {
  customer: ScoreResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CustomerRiskDrawer({ customer, open, onOpenChange }: CustomerRiskDrawerProps) {
  if (!customer) return <Sheet open={open} onOpenChange={onOpenChange}><SheetContent><div/></SheetContent></Sheet>;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader className="mb-6 border-b border-white/5 pb-6">
          <SheetTitle className="flex items-center justify-between">
            <span className="font-mono text-xl">{customer.customer_id}</span>
            <RiskBadge level={customer.risk_level} />
          </SheetTitle>
          <div className="flex gap-4 text-sm mt-4 text-muted-foreground">
            <div>
              <span className="block text-xs uppercase tracking-wider mb-1">Final Score</span>
              <span className="font-mono text-foreground text-lg">{typeof customer.final_score === 'number' ? customer.final_score.toFixed(2) : "N/A"}</span>
            </div>
            <div>
              <span className="block text-xs uppercase tracking-wider mb-1">ML Contrib</span>
              <span className="font-mono text-foreground text-lg">{typeof customer.ml_contribution === 'number' ? customer.ml_contribution.toFixed(2) : "N/A"}</span>
            </div>
          </div>
        </SheetHeader>

        <div className="space-y-8">
          <section>
            <h3 className="text-sm font-medium mb-3 text-muted-foreground uppercase tracking-wider">Triggered Rules</h3>
            {customer.triggered_rules && customer.triggered_rules.length > 0 ? (
              <div className="flex flex-col gap-2">
                {customer.triggered_rules.map((rule, idx) => (
                  <div key={idx} className="glass-panel p-3 rounded-lg border border-white/5">
                    <div className="font-medium text-sm text-foreground">{rule.rule}</div>
                    <div className="text-xs text-muted-foreground mt-1">{rule.reason}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground/50 italic">No deterministic rules triggered.</div>
            )}
          </section>

          <section>
            <h3 className="text-sm font-medium mb-3 text-muted-foreground uppercase tracking-wider">Top Risk Features (SHAP)</h3>
            {customer.top_features && customer.top_features.length > 0 ? (
              <div className="glass-panel p-4 rounded-lg border border-white/5">
                <ShapFeatureChart features={customer.top_features} />
              </div>
            ) : (
              <div className="text-sm text-muted-foreground/50 italic">No feature data available.</div>
            )}
          </section>
        </div>
      </SheetContent>
    </Sheet>
  );
}
