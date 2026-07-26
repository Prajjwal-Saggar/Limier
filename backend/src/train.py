"""
Model training and MLflow tracking script for Limier AML.
Runs on the full dataset, evaluates on a 80/20 time split,
logs metrics to MLflow, and saves models for inference.
"""
import os
import sys
import logging
import joblib
import pandas as pd
import numpy as np
import mlflow

_src = os.path.dirname(os.path.abspath(__file__))
if _src not in sys.path:
    sys.path.insert(0, _src)

from features.feature_builder import build_features
from models.ml_models import (
    prepare_feature_matrix,
    IsolationForestScorer,
    XGBoostScorer,
    MetaEnsemble,
    ML_CONFIG
)
from sklearn.metrics import average_precision_score, precision_score, recall_score, f1_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "dataset"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
os.makedirs(MODELS_DIR, exist_ok=True)

def train_and_log():
    mlflow.set_tracking_uri("sqlite:///mlruns.db")
    mlflow.set_experiment("Limier_AML_Models")
    
    with mlflow.start_run(run_name="Prod_Training"):
        logger.info("Loading transactions...")
        txns_path = os.path.join(DATA_DIR, "transactions.csv")
        if not os.path.exists(txns_path):
            logger.error(f"Data not found at {txns_path}")
            return
            
        txns = pd.read_csv(txns_path)
        txns["timestamp"] = pd.to_datetime(txns["timestamp"])
        
        logger.info("Building features...")
        features_df = build_features(txns)
        X, feature_cols = prepare_feature_matrix(features_df)
        y = (
            features_df["is_planted_suspicious"]
            if "is_planted_suspicious" in features_df.columns
            else pd.Series(0, index=X.index)
        )
        
        # Log config
        mlflow.log_params(ML_CONFIG)
        
        # Split 80/20
        split_idx = int(len(X) * 0.80)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
        
        logger.info(f"Training on {len(X_train)} samples, validating on {len(X_val)} samples.")
        
        # Train Models
        iso_scorer = IsolationForestScorer()
        iso_scorer.fit(X_train)
        
        xgb_scorer = XGBoostScorer()
        xgb_scorer.fit(X_train, y_train)
        
        # Calibrate
        iso_val_raw = iso_scorer.score_raw(X_val).values
        xgb_val_proba = xgb_scorer.score(X_val).values
        
        meta = MetaEnsemble()
        meta.fit(iso_val_raw, xgb_val_proba, y_val.values)
        
        # Evaluate
        if meta.fitted:
            ensemble_probs = meta.predict_proba(iso_val_raw, xgb_val_proba)
        else:
            ensemble_probs = 0.2 * iso_scorer.score(X_val).values + 0.8 * xgb_val_proba
            
        preds_50 = (ensemble_probs >= 0.5).astype(int)
        
        p = precision_score(y_val, preds_50, zero_division=0)
        r = recall_score(y_val, preds_50, zero_division=0)
        f = f1_score(y_val, preds_50, zero_division=0)
        ap = average_precision_score(y_val, ensemble_probs)
        
        logger.info(f"Validation Metrics - P: {p:.4f}, R: {r:.4f}, F1: {f:.4f}, AUC-PR: {ap:.4f}")
        
        mlflow.log_metrics({
            "val_precision": p,
            "val_recall": r,
            "val_f1": f,
            "val_auc_pr": ap,
        })
        
        # Save models
        logger.info("Saving models...")
        joblib.dump(iso_scorer, os.path.join(MODELS_DIR, "iso_scorer.pkl"))
        joblib.dump(xgb_scorer, os.path.join(MODELS_DIR, "xgb_scorer.pkl"))
        joblib.dump(meta, os.path.join(MODELS_DIR, "meta_ensemble.pkl"))
        
        # Log artifacts to MLflow
        mlflow.log_artifact(os.path.join(MODELS_DIR, "iso_scorer.pkl"))
        mlflow.log_artifact(os.path.join(MODELS_DIR, "xgb_scorer.pkl"))
        mlflow.log_artifact(os.path.join(MODELS_DIR, "meta_ensemble.pkl"))
        
        logger.info("Training and logging complete.")

if __name__ == "__main__":
    train_and_log()
