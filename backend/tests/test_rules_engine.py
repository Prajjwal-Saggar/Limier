"""
Tests to lock in the Rules Engine catch rate on planted high-severity typologies.
"""
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from data.generate_synthetic import generate_synthetic_data
from models.rules_engine import evaluate_all

def synthetic_data():
    """Generates a stable, seeded dataset for testing."""
    txns, custs = generate_synthetic_data(n_customers=500, days_of_history=180, seed=42)
    return txns

def test_100_percent_planted_recall(synthetic_data):
    """
    Validates that the rules engine catches 100% of planted high-severity patterns.
    """
    txns = synthetic_data
    
    # 1. Apply the noise filter threshold used in production orchestration
    significant_txns = txns[txns["amount"] >= 8000].copy()
    
    # 2. Evaluate all rules
    rule_results = evaluate_all(significant_txns)
    
    # 3. Identify planted high-severity customers
    high_sev_patterns = ["structuring", "rapid_cashout", "round_trip"]
    planted_high = txns[txns["planted_pattern"].isin(high_sev_patterns)]["customer_id"].unique()
    
    # 4. Verify 100% catch rate
    caught_count = 0
    missed_customers = []
    
    for cid in planted_high:
        res = rule_results.get(cid, [])
        if any(r.severity == "high" for r in res):
            caught_count += 1
        else:
            missed_customers.append(cid)
            
    assert caught_count == len(planted_high), f"Missed planted high-severity customers: {missed_customers}"
    assert caught_count > 0, "No planted patterns were generated to test!"

if __name__ == "__main__":
    txns = synthetic_data()
    test_100_percent_planted_recall(txns)
    print("ALL TESTS PASSED: 100% planted recall verified.")
