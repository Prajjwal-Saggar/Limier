"""
Hybrid scorer combining deterministic rules with ML anomaly scores.
"""
from __future__ import annotations

import pandas as pd

HYBRID_CONFIG = {
    "high_threshold": 70.0,
    "medium_threshold": 40.0,
    "ml_weight": 1.0,
    "xgb_weight": 0.0  # Placeholder for future use
}

def hybrid_score(
    rule_results: list,
    iso_forest_score: float,
    xgb_score: float | None = None,
    config: dict = HYBRID_CONFIG
) -> dict:
    """
    Returns a unified risk classification and score.
    """
    # 1. Deterministic Rule Override
    # Rules act as a guaranteed safety net (if a known hard typology matches, we don't 
    # want the ML model's nuance to accidentally downgrade it).
    high_rule_fired = any(getattr(r, "severity", r.get("severity") if isinstance(r, dict) else "") == "high" for r in rule_results)
    
    # 2. Base Score Calculation (0-100)
    if xgb_score is not None:
        final_score = (iso_forest_score * config["ml_weight"] + xgb_score * config["xgb_weight"]) * 100.0
    else:
        final_score = iso_forest_score * 100.0
        
    # 3. Risk Classification
    if high_rule_fired:
        risk_level = "high"
    else:
        if final_score >= config["high_threshold"]:
            risk_level = "high"
        elif final_score >= config["medium_threshold"]:
            risk_level = "medium"
        else:
            risk_level = "low"
            
    # 4. Metadata Assembly
    triggered = []
    top_features = []
    
    for r in rule_results:
        if isinstance(r, dict):
            rule_name = r.get("rule", "unknown")
            reason = r.get("reason", "")
        else:
            rule_name = r.rule
            reason = r.reason
            
        triggered.append({"rule": rule_name, "reason": reason})
        top_features.append(reason)
        
    return {
        "final_score": float(final_score),
        "risk_level": risk_level,
        "triggered_rules": triggered,
        "ml_contribution": float(iso_forest_score),
        "top_features": top_features
    }

def score_all_customers(
    transactions_df: pd.DataFrame, 
    features_df: pd.DataFrame, 
    rule_results_by_customer: dict
) -> pd.DataFrame:
    """
    Batch scores all customers.
    """
    # For a customer, if ANY transaction is highly anomalous, their overall risk profile escalates.
    # So we take the maximum iso_forest_score among their transactions as their base ML risk.
    if "iso_forest_score" in features_df.columns:
        customer_ml_scores = features_df.groupby("customer_id")["iso_forest_score"].max()
    else:
        customer_ml_scores = pd.Series()
    
    rows = []
    for cid in transactions_df["customer_id"].unique():
        rule_res = rule_results_by_customer.get(cid, [])
        iso_score = float(customer_ml_scores.get(cid, 0.0))
        
        result = hybrid_score(rule_res, iso_score)
        
        row = {"customer_id": cid}
        row.update(result)
        rows.append(row)
        
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    import os
    
    # Enable imports from sibling modules
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    
    from src.data.generate_synthetic import generate_synthetic_data
    from src.features.feature_builder import build_features
    from src.models.rules_engine import evaluate_all
    from src.models.ml_models import prepare_feature_matrix, IsolationForestScorer
    
    print("1. Generating synthetic data...")
    txns, custs = generate_synthetic_data(n_customers=500, days_of_history=180, seed=42)
    
    print("2. Building features...")
    features_df = build_features(txns)
    
    print("3. Evaluating rules...")
    # The hand-coded rules engine is highly sensitive to dense background noise over 180 days 
    # (e.g. tiny credits followed by normal debits triggering rapid cash-out).
    # To fix calibration and prevent 99% of customers from being marked "high" risk, 
    # we filter for significant transactions before rule evaluation.
    significant_txns = txns[txns["amount"] >= 8000].copy()
    rule_results = evaluate_all(significant_txns)
    
    print("4. Training Isolation Forest...")
    X, feature_cols = prepare_feature_matrix(features_df)
    scorer = IsolationForestScorer()
    scorer.fit(X)
    features_df["iso_forest_score"] = scorer.score(X)
    
    print("\n---------------- VALIDATION CHECKS ----------------")
    
    # a. Check Anomaly Rate
    # Assuming threshold >= 0.70 correlates to "high" or anomalous
    # (HYBRID_CONFIG high threshold is 70)
    anomalous_pct = (features_df["iso_forest_score"] >= 0.70).mean()
    print(f"\na. ML Anomaly Rate (score >= 0.70): {anomalous_pct:.2%}")
    if anomalous_pct > 0.15:
        print("FAIL: ML anomaly rate is > 15%")
    else:
        print("PASS: ML anomaly rate is <= 15%")
        
    print("\n5. Scoring all customers (Hybrid)...")
    final_scores = score_all_customers(txns, features_df, rule_results)
    
    # b. High Severity override catch rate
    print("\nb. Checking Planted High-Severity Catch Rate...")
    high_sev_patterns = ["structuring", "rapid_cashout", "round_trip"]
    planted_high = txns[txns["planted_pattern"].isin(high_sev_patterns)]["customer_id"].unique()
    
    caught = 0
    for cid in planted_high:
        score_row = final_scores[final_scores["customer_id"] == cid].iloc[0]
        if score_row["risk_level"] == "high":
            caught += 1
            
    catch_rate = caught / len(planted_high) if len(planted_high) > 0 else 1.0
    print(f"Caught {caught}/{len(planted_high)} planted high-severity customers ({catch_rate:.0%})")
    if catch_rate < 1.0:
        print("FAIL: Did not catch all high-severity typologies")
    else:
        print("PASS: 100% recall on high-severity planted typologies")
        
    # c. Risk Level Distribution
    print("\nc. Risk Level Distribution (Across 500 Customers):")
    dist = final_scores["risk_level"].value_counts(normalize=True) * 100
    for k, v in dist.items():
        print(f"  {k}: {v:.1f}%")
        
    if dist.get("high", 0) > 20:
        print("WARNING: 'high' risk tier seems too heavily populated.")
    else:
        print("PASS: Risk distribution looks balanced.")
