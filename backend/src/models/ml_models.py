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

class XGBoostScorer:
    def __init__(self, config: dict = ML_CONFIG):
        import xgboost as xgb
        self.model = xgb.XGBClassifier(
            n_estimators=config["n_estimators"],
            learning_rate=0.1,
            max_depth=4,
            random_state=config["random_state"],
            n_jobs=-1,
            eval_metric="logloss"
        )
        self.explainer = None
        self.feature_cols = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Trains the XGBoost model on ground truth labels."""
        self.model.fit(X, y)
        self.feature_cols = X.columns.tolist()
        
        # Initialize SHAP explainer for explainability
        import shap
        self.explainer = shap.TreeExplainer(self.model)

    def score(self, X: pd.DataFrame) -> pd.Series:
        """Returns the probability (0-1) of the transaction being anomalous."""
        # predict_proba returns [P(class 0), P(class 1)]
        return pd.Series(self.model.predict_proba(X)[:, 1], index=X.index)

    def get_top_features(self, X: pd.DataFrame, top_k: int = 5) -> list[list[dict]]:
        """
        Returns the top_k feature details driving the anomaly score for each row in X.
        Useful for generating human-readable explanations via the agent.
        """
        if self.explainer is None:
            return [[] for _ in range(len(X))]
            
        shap_values = self.explainer.shap_values(X)
        
        # XGBClassifier shap_values might be 2D or a list depending on objective.
        # For binary classification it's usually a 2D array of shape (n_samples, n_features).
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
            
        top_features_per_row = []
        for i in range(len(X)):
            # Sort features by absolute SHAP value (impact magnitude)
            row_shap = shap_values[i]
            row_abs_shap = np.abs(row_shap)
            top_indices = np.argsort(row_abs_shap)[-top_k:][::-1]
            row_features = []
            for idx in top_indices:
                row_features.append({
                    "feature": self.feature_cols[idx],
                    "value": float(X.iloc[i, idx]),
                    "shap_contribution": float(row_shap[idx])
                })
            top_features_per_row.append(row_features)
            
        return top_features_per_row
