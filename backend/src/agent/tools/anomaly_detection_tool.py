"""
ML anomaly scoring tool for AI agents.
"""
import pandas as pd
from typing import Tuple

from src.features.feature_builder import build_features
from src.models.ml_models import prepare_feature_matrix, IsolationForestScorer

def detect_anomalies(transactions_df: pd.DataFrame) -> Tuple[pd.DataFrame, IsolationForestScorer]:
    """
    Computes features for raw transactions and runs unsupervised anomaly detection.
    
    Args:
        transactions_df: DataFrame containing raw transaction history.
        
    Returns:
        Tuple containing:
        - features_df (pd.DataFrame): The feature matrix with an appended 'iso_forest_score' column.
        - model (IsolationForestScorer): The fitted model instance.
    """
    if transactions_df.empty:
        return pd.DataFrame(), None
        
    # 1. Build AML features from raw transactions
    features_df = build_features(transactions_df)
    
    # 2. Prepare feature matrix for the ML model (handles imputation, drops categorical IDs)
    X, feature_cols = prepare_feature_matrix(features_df)
    
    # 3. Initialize and fit the Isolation Forest model
    scorer = IsolationForestScorer()
    scorer.fit(X)
    
    # 4. Generate normalized (0-1) anomaly scores
    features_df["iso_forest_score"] = scorer.score(X)
    
    return features_df, scorer
