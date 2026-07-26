import pandas as pd
import numpy as np
import pytest
from src.models.ml_models import IsolationForestScorer, XGBoostScorer, MetaEnsemble, prepare_feature_matrix

def test_prepare_feature_matrix():
    data = {
        "transaction_id": ["T1"],
        "customer_id": ["C1"],
        "amount": [100.0],
        "is_planted_suspicious": [0],
        "planted_pattern": [np.nan],
        "spike_ratio": [np.nan],
        "feature1": [1.0]
    }
    df = pd.DataFrame(data)
    
    X, feature_cols = prepare_feature_matrix(df)
    
    assert "transaction_id" not in X.columns
    assert "customer_id" not in X.columns
    assert "spike_ratio_has_history" in X.columns
    assert X["spike_ratio"].isna().sum() == 0

def test_meta_ensemble():
    meta = MetaEnsemble()
    
    # Too few positives test
    iso = np.random.rand(10)
    xgb = np.random.rand(10)
    y = np.array([0]*10)
    
    meta.fit(iso, xgb, y)
    assert meta.fitted == False
    
    # Fallback score test
    probs = meta.predict_proba(np.array([0.5]), np.array([0.5]))
    assert len(probs) == 1
    assert probs[0] == 0.5  # 0.2*0.5 + 0.8*0.5

