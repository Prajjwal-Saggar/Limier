"""
Machine learning anomaly detection layer using Isolation Forest.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MinMaxScaler

ML_CONFIG = {
    # Isolation Forest
    "n_estimators": 100,
    "contamination": 0.01,
    "random_state": 42,

    # XGBoost — tuned via Optuna (30 trials, AUC-PR objective on 70/30 time-split)
    # Baseline AUC-PR: 0.8858 | Post-tuning AUC-PR: 0.9265 (+4.6% relative improvement)
    "xgb_n_estimators": 288,
    "xgb_max_depth": 6,
    "xgb_learning_rate": 0.2705,
    "xgb_min_child_weight": 4,
    "xgb_subsample": 0.826,
    "xgb_colsample_bytree": 0.519,
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
        raw_scores = -self.model.decision_function(X)
        normalized = self.scaler.fit_transform(raw_scores.reshape(-1, 1)).flatten()
        return pd.Series(normalized, index=X.index)

    def score_raw(self, X: pd.DataFrame) -> pd.Series:
        """
        Returns raw (negated) decision function values — NOT MinMax normalized.
        These are the values used by MetaEnsemble for Platt calibration.
        Higher = more anomalous (same direction as score()).
        """
        return pd.Series(-self.model.decision_function(X), index=X.index)

class XGBoostScorer:
    def __init__(self, config: dict = ML_CONFIG):
        import xgboost as xgb
        self.model = xgb.XGBClassifier(
            n_estimators=config.get("xgb_n_estimators", 288),
            learning_rate=config.get("xgb_learning_rate", 0.2705),
            max_depth=config.get("xgb_max_depth", 6),
            min_child_weight=config.get("xgb_min_child_weight", 4),
            subsample=config.get("xgb_subsample", 0.826),
            colsample_bytree=config.get("xgb_colsample_bytree", 0.519),
            random_state=config.get("random_state", 42),
            n_jobs=-1,
            eval_metric="logloss",
            verbosity=0,
        )
        self.explainer = None
        self.feature_cols = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Trains the XGBoost model on ground truth labels."""
        # Calculate scale_pos_weight dynamically to handle class imbalance
        num_neg = (y == 0).sum()
        num_pos = (y == 1).sum()
        scale_pos_weight = float(num_neg / num_pos) if num_pos > 0 else 1.0
        
        self.model.set_params(scale_pos_weight=scale_pos_weight)
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


class MetaEnsemble:
    """
    Calibrated ensemble that combines Isolation Forest and XGBoost scores
    using Platt scaling + a 2-feature logistic regression meta-model.

    WHY THIS MATTERS:
    - IF produces tree-depth-based anomaly scores — NOT probabilities.
    - XGBoost with scale_pos_weight produces probabilities, but they're
      biased upward due to cost-sensitive learning and need re-calibration.
    - Averaging the two raw outputs on the same 0-1 scale conflates
      completely different distributional spaces.
    - Platt scaling (sigmoid logistic regression) maps each score to
      P(fraud | score), putting both on the same probability scale.
    - A final 2-feature logistic meta-model then learns the OPTIMAL BLEND
      from labeled validation data rather than guessing weights by hand.
    """

    def __init__(self):
        self.iso_calibrator: LogisticRegression | None = None  # IF raw → P(fraud)
        self.meta_model: LogisticRegression | None = None      # [P_if, P_xgb] → P(fraud)
        self.fitted = False

    def fit(
        self,
        iso_raw_scores: np.ndarray,  # negated IF decision_function values
        xgb_proba: np.ndarray,       # XGB predict_proba[:, 1]
        y: np.ndarray                # true labels (0/1)
    ) -> None:
        """
        Fit Platt calibrators and logistic meta-model on VALIDATION data.
        This must be called with out-of-sample predictions (never training data).
        """
        if y.sum() < 5:
            # Too few positives to calibrate — fall back to heuristic
            self.fitted = False
            return

        # Platt Scaling for Isolation Forest
        # A 1-feature logistic regression maps raw IF score → P(fraud)
        self.iso_calibrator = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced")
        self.iso_calibrator.fit(iso_raw_scores.reshape(-1, 1), y)

        cal_if = self.iso_calibrator.predict_proba(iso_raw_scores.reshape(-1, 1))[:, 1]

        # 2-feature logistic meta-model: learns optimal blend from labeled val data
        X_meta = np.column_stack([cal_if, xgb_proba])
        self.meta_model = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced")
        self.meta_model.fit(X_meta, y)
        self.fitted = True

    def predict_proba(self, iso_raw_scores: np.ndarray, xgb_proba: np.ndarray) -> np.ndarray:
        """
        Returns calibrated P(fraud) for each sample.
        Falls back to the heuristic 0.2/0.8 weighted average if not fitted.
        """
        if not self.fitted or self.iso_calibrator is None or self.meta_model is None:
            # Heuristic fallback (prior behavior)
            return 0.2 * iso_raw_scores + 0.8 * xgb_proba

        cal_if = self.iso_calibrator.predict_proba(iso_raw_scores.reshape(-1, 1))[:, 1]
        X_meta = np.column_stack([cal_if, xgb_proba])
        return self.meta_model.predict_proba(X_meta)[:, 1]
