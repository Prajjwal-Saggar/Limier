"""
Machine learning anomaly detection layer using Isolation Forest.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler

ML_CONFIG = {
    "n_estimators": 100,
    "contamination": 0.05,
    "random_state": 42
}

def prepare_feature_matrix(features_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Select numeric columns for ML and handle cold-start NaNs dynamically.
    """
    # 1. Exclude non-numeric IDs and raw amount
    # (We use log_amount instead to avoid scale dominance)
    drop_cols = ["transaction_id", "customer_id", "amount", "is_planted_suspicious", "planted_pattern"]
    base_cols = [c for c in features_df.columns if c not in drop_cols]
    
    df = features_df[base_cols].copy()
    
    # 2. Handle spike_ratio missingness
    # Explicitly track whether the customer has enough history (1 = has history, 0 = no history)
    df["spike_ratio_has_history"] = (~df["spike_ratio"].isna()).astype(int)
    
    # Impute missing spike_ratio with the median of non-NaN values
    median_spike = df["spike_ratio"].median()
    df["spike_ratio"] = df["spike_ratio"].fillna(median_spike)
    
    # Fill any remaining generic NaNs just in case (to guarantee IsolationForest fit won't crash)
    df = df.fillna(0.0)
    
    feature_cols = df.columns.tolist()
    return df, feature_cols

class IsolationForestScorer:
    def __init__(self, config: dict = ML_CONFIG):
        self.model = IsolationForest(
            n_estimators=config["n_estimators"],
            contamination=config["contamination"],
            random_state=config["random_state"],
            n_jobs=-1
        )
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def fit(self, X: pd.DataFrame) -> None:
        """Trains the Isolation Forest model."""
        self.model.fit(X)

    def score(self, X: pd.DataFrame) -> pd.Series:
        """
        Returns a normalized 0-1 anomaly score where higher = more anomalous.
        """
        # decision_function returns anomaly scores (lower = more anomalous in sklearn).
        # We negate it so higher = more anomalous.
        raw_scores = -self.model.decision_function(X)
        
        # We rescale to exactly 0-1 using MinMax. 
        # MinMax scaler cleanly bounds the anomaly score for deterministic combination with rules.
        # (It uses the theoretical or observed min/max of the tree depth bounds in the current fit).
        normalized = self.scaler.fit_transform(raw_scores.reshape(-1, 1)).flatten()
        
        return pd.Series(normalized, index=X.index)
