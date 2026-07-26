"""
ML anomaly scoring tool.
Time-based 80/20 train/validation split:
  - Train: IF + XGBoost fitted on oldest 80% of transactions.
  - Validation: MetaEnsemble (Platt + logistic meta-model) fitted on
    out-of-sample val predictions — strictly no leakage.
  - Inference: All transactions scored using calibrated meta-ensemble.
"""
import os
import logging
import numpy as np
import pandas as pd
from typing import Tuple

from src.features.feature_builder import build_features
from src.models.ml_models import (
    prepare_feature_matrix,
    IsolationForestScorer,
    XGBoostScorer,
    MetaEnsemble,
)

logger = logging.getLogger(__name__)


def detect_anomalies(
    transactions_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, IsolationForestScorer, XGBoostScorer, MetaEnsemble]:
    """
    Returns (features_df, iso_scorer, xgb_scorer, meta_ensemble).
    features_df gets columns: iso_forest_score, iso_forest_score_raw,
    xgb_score, ensemble_score, shap_features.
    """
    if transactions_df.empty:
        return pd.DataFrame(), None, None, MetaEnsemble()

    # 1. Build AML features
    features_df = build_features(transactions_df)

    # 2. Prepare feature matrix
    X, feature_cols = prepare_feature_matrix(features_df)
    y = (
        features_df["is_planted_suspicious"]
        if "is_planted_suspicious" in features_df.columns
        else pd.Series(0, index=X.index)
    )

    MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models"))
    iso_path = os.path.join(MODELS_DIR, "iso_scorer.pkl")
    xgb_path = os.path.join(MODELS_DIR, "xgb_scorer.pkl")
    meta_path = os.path.join(MODELS_DIR, "meta_ensemble.pkl")

    models_exist = os.path.exists(iso_path) and os.path.exists(xgb_path) and os.path.exists(meta_path)

    if models_exist:
        logger.info("Loading persisted models from disk...")
        import joblib
        iso_scorer = joblib.load(iso_path)
        xgb_scorer = joblib.load(xgb_path)
        meta = joblib.load(meta_path)
    else:
        logger.info("Persisted models not found. Falling back to dynamic training on 80/20 split...")
        # 3. Time-based 80/20 split
        split_idx = int(len(X) * 0.80)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
        n_pos_val = int(y_val.sum())
        logger.info(f"Train={len(X_train)} Val={len(X_val)} Val_positives={n_pos_val}")

        # 4. Fit IF on TRAIN
        iso_scorer = IsolationForestScorer()
        iso_scorer.fit(X_train)

        # 5. Fit XGBoost on TRAIN
        xgb_scorer = XGBoostScorer()
        xgb_scorer.fit(X_train, y_train)

        # 6. Out-of-sample val predictions for calibration
        iso_val_raw = iso_scorer.score_raw(X_val).values
        xgb_val_proba = xgb_scorer.score(X_val).values

        # 7. Fit MetaEnsemble on VAL (out-of-sample — no leakage)
        meta = MetaEnsemble()
        meta.fit(iso_val_raw, xgb_val_proba, y_val.values)
        if meta.fitted:
            logger.info("MetaEnsemble: Platt + logistic meta-model fitted.")
        else:
            logger.warning(f"MetaEnsemble: too few positives ({n_pos_val}), using heuristic fallback.")

    # 8. Score ALL data with calibrated models
    features_df["iso_forest_score_raw"] = iso_scorer.score_raw(X).values
    features_df["iso_forest_score"] = iso_scorer.score(X).values
    features_df["xgb_score"] = xgb_scorer.score(X).values
    features_df["ensemble_score"] = meta.predict_proba(
        features_df["iso_forest_score_raw"].values,
        features_df["xgb_score"].values,
    )

    # 9. SHAP explanations
    features_df["shap_features"] = xgb_scorer.get_top_features(X)

    return features_df, iso_scorer, xgb_scorer, meta

