export interface HealthResponse {
  status: string;
  cached: boolean;
}

export interface EdaResponse {
  total_customers: number;
  total_transactions: number;
  date_range: {
    from: string;
    to: string;
  };
  amount_distribution: {
    mean: number;
    median: number;
    std: number;
    p95: number;
    p99: number;
  };
  transactions_by_channel: Record<string, number>;
  transactions_by_type: Record<string, number>;
  cross_border_pct: number;
  missing_value_summary: Record<string, number>;
  risk_level_breakdown: {
    low?: number;
    medium?: number;
    high?: number;
  };
}

export interface TriggeredRule {
  rule: string;
  reason: string;
}

export interface TopFeature {
  feature: string;
  value: number;
  shap_contribution?: number;
}

export interface CustomerRiskResponse {
  customer_id: string;
  risk_level: "low" | "medium" | "high";
  final_score: number;
  ml_contribution: number;
  triggered_rules: TriggeredRule[];
  top_features: TopFeature[];
  recent_transaction_count: number;
  account_age_days: number;
}

export interface ScoreResponse {
  customer_id: string;
  risk_level: "low" | "medium" | "high";
  final_score: number;
  ml_contribution: number;
  triggered_rules: TriggeredRule[];
  top_features: TopFeature[];
}

export interface ScoreFilterOptions {
  customer_ids?: string[];
  date_from?: string;
  date_to?: string;
  pattern_focus?: string;
  min_risk_level?: string;
}

export interface ScoreRequest {
  transactions?: any[];
  filters?: ScoreFilterOptions;
}

export type AgentEventType = "intent_detected" | "tool_call" | "tool_result" | "final_answer" | "error";

export interface AgentEvent {
  type: AgentEventType;
  data: any;
}
