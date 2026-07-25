"""
Builds AML features on demand.
Generates Category A, B, and C features for ML models and rules.
"""

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
FEATURE_CONFIG = {
    # Category A: Structuring & Amounts
    "structuring_min_amount": 9000.0,
    "structuring_max_amount": 9999.99,
    "ctr_threshold": 10000.0,
    "subthreshold_max_amount": 10000.0,
    "subthreshold_sum_window": "24h",
    "structuring_count_window": "7D",

    # Category B: Frequency & Velocity
    "window_1d": "1D",
    "window_7d": "7D",
    "window_30d": "30D",
    "spike_current_window": "7D",
    "spike_total_lookback_days": 63,  # 7 days current + 56 days (8 weeks) trailing
    "spike_trailing_weeks": 8.0,
    "burstiness_window": "30D",

    # Category C: Cash-flow & Directionality
    "rapid_cashout_inflow_window": "48h",
    "rapid_cashout_outflow_window": "24h",
    "round_trip_window_days": 10.0,
}

# --------------------------------------------------------------------------- #
# Main Feature Builder
# --------------------------------------------------------------------------- #
def build_features(transactions_df: pd.DataFrame, customer_id: str | None = None) -> pd.DataFrame:
    """
    Build features for Category A, B, and C.
    Returns a DataFrame aligned with the input, containing transaction_id, customer_id,
    and all computed features. 
    """
    if transactions_df.empty:
        return pd.DataFrame()

    df = transactions_df.copy()
    if customer_id is not None:
        df = df[df["customer_id"] == customer_id].copy()

    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Pre-sort by customer and time to allow efficient rolling operations
    df = df.sort_values(["customer_id", "timestamp"]).reset_index(drop=True)

    # ----------------------------------------------------------------------- #
    # Helper Columns (Not final features)
    # ----------------------------------------------------------------------- #
    df["is_credit"] = df["direction"] == "credit"
    df["is_debit"] = df["direction"] == "debit"
    df["inflow_amount"] = df["amount"].where(df["is_credit"], 0.0)
    df["outflow_amount"] = df["amount"].where(df["is_debit"], 0.0)
    
    df["is_structuring_range"] = (df["amount"] >= FEATURE_CONFIG["structuring_min_amount"]) & \
                                 (df["amount"] <= FEATURE_CONFIG["structuring_max_amount"])
    df["subthreshold_amount"] = df["amount"].where(df["amount"] < FEATURE_CONFIG["subthreshold_max_amount"], 0.0)
    
    # Factorize counterparty for fast distinct counting
    df["cp_id_num"] = df["counterparty_id"].factorize()[0]
    df["credit_cp"] = df["cp_id_num"].where(df["is_credit"], np.nan)
    df["debit_cp"] = df["cp_id_num"].where(df["is_debit"], np.nan)

    # ----------------------------------------------------------------------- #
    # GroupBy object setup
    # ----------------------------------------------------------------------- #
    grp = df.groupby("customer_id")

    # ----------------------------------------------------------------------- #
    # CATEGORY A — Amount & structuring features
    # ----------------------------------------------------------------------- #
    df["log_amount"] = np.log1p(df["amount"])
    df["amount_rounded_to_nearest_100"] = (df["amount"] % 100 == 0).astype(int)
    df["distance_from_ctr_threshold"] = FEATURE_CONFIG["ctr_threshold"] - df["amount"]
    
    df["count_subthreshold_txns_7d"] = grp.rolling(FEATURE_CONFIG["structuring_count_window"], on="timestamp")["is_structuring_range"].sum().reset_index(drop=True)
    df["sum_subthreshold_txns_24h"] = grp.rolling(FEATURE_CONFIG["subthreshold_sum_window"], on="timestamp")["subthreshold_amount"].sum().reset_index(drop=True)
    
    total_txns_7d = grp.rolling(FEATURE_CONFIG["window_7d"], on="timestamp")["amount"].count().reset_index(drop=True)
    df["ratio_subthreshold_to_total_txns"] = (df["count_subthreshold_txns_7d"] / total_txns_7d.replace(0, 1)).fillna(0.0)

    # ----------------------------------------------------------------------- #
    # CATEGORY B — Frequency & velocity features
    # ----------------------------------------------------------------------- #
    df["txn_count_1d"] = grp.rolling(FEATURE_CONFIG["window_1d"], on="timestamp")["amount"].count().reset_index(drop=True)
    df["txn_count_7d"] = total_txns_7d
    df["txn_count_30d"] = grp.rolling(FEATURE_CONFIG["window_30d"], on="timestamp")["amount"].count().reset_index(drop=True)
    
    df["txn_velocity"] = df["txn_count_7d"] / 7.0
    
    # Dormancy / Burstiness
    df["gap_days"] = grp["timestamp"].diff().dt.total_seconds() / 86400.0
    df["days_since_last_txn"] = df["gap_days"].fillna(0.0)
    
    rolling_gap = grp.rolling(FEATURE_CONFIG["burstiness_window"], on="timestamp")["gap_days"]
    gap_mean = rolling_gap.mean().reset_index(drop=True)
    gap_std = rolling_gap.std().reset_index(drop=True)
    df["burstiness"] = (gap_std / gap_mean.replace(0, np.nan)).fillna(0.0)
    
    # Spike ratio (Current week vs trailing 8 weeks)
    total_lookback_str = f"{FEATURE_CONFIG['spike_total_lookback_days']}D"
    count_63d = grp.rolling(total_lookback_str, on="timestamp")["amount"].count().reset_index(drop=True)
    trailing_8wk_count = count_63d - df["txn_count_7d"]
    trailing_avg_weekly = trailing_8wk_count / FEATURE_CONFIG["spike_trailing_weeks"]
    
    # Calculate days since the customer's first transaction
    customer_start_ts = grp["timestamp"].transform("min")
    days_since_first_txn = (df["timestamp"] - customer_start_ts).dt.total_seconds() / 86400.0
    has_enough_history = days_since_first_txn >= (FEATURE_CONFIG["spike_trailing_weeks"] * 7)
    
    # NaN is correct here for early transactions: new customers shouldn't be penalized as anomalies 
    # just because they lack trailing history for the denominator.
    # We preserve the 0.1 replacement *only* for established but inactive customers.
    df["spike_ratio"] = (df["txn_count_7d"] / trailing_avg_weekly.replace(0, 0.1)).where(has_enough_history, np.nan)

    # ----------------------------------------------------------------------- #
    # CATEGORY C — Cash-flow & directionality features
    # ----------------------------------------------------------------------- #
    df["rolling_inflow_sum_7d"] = grp.rolling(FEATURE_CONFIG["window_7d"], on="timestamp")["inflow_amount"].sum().reset_index(drop=True)
    df["rolling_inflow_sum_30d"] = grp.rolling(FEATURE_CONFIG["window_30d"], on="timestamp")["inflow_amount"].sum().reset_index(drop=True)
    
    df["rolling_outflow_sum_7d"] = grp.rolling(FEATURE_CONFIG["window_7d"], on="timestamp")["outflow_amount"].sum().reset_index(drop=True)
    df["rolling_outflow_sum_30d"] = grp.rolling(FEATURE_CONFIG["window_30d"], on="timestamp")["outflow_amount"].sum().reset_index(drop=True)
    
    df["net_flow"] = df["rolling_inflow_sum_30d"] - df["rolling_outflow_sum_30d"]
    
    # Rapid cashout
    outflow_24h = grp.rolling(FEATURE_CONFIG["rapid_cashout_outflow_window"], on="timestamp")["outflow_amount"].sum().reset_index(drop=True)
    inflow_48h = grp.rolling(FEATURE_CONFIG["rapid_cashout_inflow_window"], on="timestamp")["inflow_amount"].sum().reset_index(drop=True)
    df["rapid_cashout_ratio"] = (outflow_24h / inflow_48h.replace(0, np.nan)).fillna(0.0)
    
    # Fan in / out
    df["fan_in_count"] = grp.rolling(FEATURE_CONFIG["window_30d"], on="timestamp")["credit_cp"].apply(
        lambda x: len(np.unique(x[~np.isnan(x)])) if len(x) > 0 else 0, raw=True
    ).reset_index(drop=True).fillna(0.0)
    
    df["fan_out_count"] = grp.rolling(FEATURE_CONFIG["window_30d"], on="timestamp")["debit_cp"].apply(
        lambda x: len(np.unique(x[~np.isnan(x)])) if len(x) > 0 else 0, raw=True
    ).reset_index(drop=True).fillna(0.0)
    
    # Round trip flag
    cp_grp = df.groupby(["customer_id", "counterparty_id"])
    df["debit_ts"] = df["timestamp"].where(df["is_debit"])
    df["credit_ts"] = df["timestamp"].where(df["is_credit"])
    
    last_debit_ts = cp_grp["debit_ts"].ffill()
    last_credit_ts = cp_grp["credit_ts"].ffill()
    
    days_since_debit = (df["timestamp"] - last_debit_ts).dt.total_seconds() / 86400.0
    days_since_credit = (df["timestamp"] - last_credit_ts).dt.total_seconds() / 86400.0
    
    rt_debit_to_credit = df["is_credit"] & (days_since_debit <= FEATURE_CONFIG["round_trip_window_days"])
    rt_credit_to_debit = df["is_debit"] & (days_since_credit <= FEATURE_CONFIG["round_trip_window_days"])
    df["round_trip_flag"] = (rt_debit_to_credit | rt_credit_to_debit).astype(int)

    # ----------------------------------------------------------------------- #
    # Final Output Selection
    # ----------------------------------------------------------------------- #
    feature_cols = [
        "transaction_id", "customer_id", "amount", 
        
        # Category A
        "log_amount", "amount_rounded_to_nearest_100", "distance_from_ctr_threshold",
        "count_subthreshold_txns_7d", "sum_subthreshold_txns_24h", "ratio_subthreshold_to_total_txns",
        
        # Category B
        "txn_count_1d", "txn_count_7d", "txn_count_30d", "txn_velocity",
        "days_since_last_txn", "spike_ratio", "burstiness",
        
        # Category C
        "rolling_inflow_sum_7d", "rolling_inflow_sum_30d",
        "rolling_outflow_sum_7d", "rolling_outflow_sum_30d",
        "net_flow", "rapid_cashout_ratio", 
        "fan_in_count", "fan_out_count", "round_trip_flag"
    ]
    
    return df[feature_cols].copy()


if __name__ == "__main__":
    import sys
    import os
    
    # Enable imports from sibling modules
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from src.data.generate_synthetic import generate_synthetic_data
    
    print("Generating sample dataset (300 customers, 180 days)...")
    txns, custs = generate_synthetic_data(n_customers=300, days_of_history=180, seed=42)
    
    print("Building features...")
    features_df = build_features(txns)
    
    print(f"\nTotal transactions generated: {len(txns)}")
    print(f"Total feature rows produced: {len(features_df)}")
    
    # Check for NaNs
    nan_counts = features_df.isna().sum()
    if nan_counts.sum() > 0:
        print("\nNaN counts per column (expected for spike_ratio):")
        print(nan_counts[nan_counts > 0])
    else:
        print("\nSUCCESS - No NaN values found in feature output.")
        
    print("\nSanity Check: Spike Ratio NaNs")
    # Spot check 2-3 customers
    sample_customers = txns["customer_id"].unique()[:3]
    for cid in sample_customers:
        print(f"\nCustomer {cid} first 10 transactions:")
        subset = features_df[features_df["customer_id"] == cid].head(10)
        first_ts = txns[txns["customer_id"] == cid]["timestamp"].min()
        subset_txns = txns[txns["customer_id"] == cid].head(10)
        days_since_first = (subset_txns["timestamp"] - first_ts).dt.total_seconds() / 86400.0
        
        display_df = pd.DataFrame({
            "txn_idx": range(1, len(subset) + 1),
            "days_since_first": days_since_first.values.round(1),
            "spike_ratio": subset["spike_ratio"].values
        })
        print(display_df.to_string(index=False))

    # merge planted truth and timestamps for testing
    merged = pd.merge(features_df, txns[["transaction_id", "timestamp", "is_planted_suspicious", "planted_pattern"]], on="transaction_id")
    
    # Check an established customer with a genuine long history
    print("\nSanity Check: Spike Ratio for established customers")
    established_mask = (merged["timestamp"] - merged.groupby("customer_id")["timestamp"].transform("min")).dt.total_seconds() / 86400.0 >= 56
    established_features = merged[established_mask]
    nan_established = established_features["spike_ratio"].isna().sum()
    print(f"NaN spike_ratios for transactions >= 56 days old: {nan_established} (Expected: 0)")
    
    # Check if a dormant_then_active planted spike is caught and not NaNed
    dormant_cases = merged[merged["planted_pattern"] == "dormant_then_active"]["customer_id"].unique()
    if len(dormant_cases) > 0:
        dormant_cid = dormant_cases[0]
        print(f"\nSpot check for planted dormant_then_active customer {dormant_cid} (last 5 txns):")
        dormant_subset = merged[merged["customer_id"] == dormant_cid].tail(5)
        print(dormant_subset[["transaction_id", "spike_ratio"]].to_string(index=False))
        
    # Sanity check: structuring
    print("\nSanity Check: Structuring planted vs normal")
    
    normal_avg = merged[~merged["is_planted_suspicious"]]["count_subthreshold_txns_7d"].mean()
    structuring_avg = merged[merged["planted_pattern"] == "structuring"]["count_subthreshold_txns_7d"].mean()
    
    print(f"Average count_subthreshold_txns_7d for NORMAL txns: {normal_avg:.2f}")
    print(f"Average count_subthreshold_txns_7d for STRUCTURING txns: {structuring_avg:.2f}")
    
    normal_ratio = merged[~merged["is_planted_suspicious"]]["ratio_subthreshold_to_total_txns"].mean()
    structuring_ratio = merged[merged["planted_pattern"] == "structuring"]["ratio_subthreshold_to_total_txns"].mean()
    
    print(f"Average ratio_subthreshold_to_total_txns for NORMAL txns: {normal_ratio:.2%}")
    print(f"Average ratio_subthreshold_to_total_txns for STRUCTURING txns: {structuring_ratio:.2%}")
    
    # Basic bounds check on ratio
    assert normal_ratio < structuring_ratio, "Structuring txns should have a higher subthreshold ratio!"
    assert normal_avg < structuring_avg, "Structuring txns should have a higher subthreshold count!"
    
    print("\nAll checks passed successfully.")
