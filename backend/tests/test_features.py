import pandas as pd
import pytest
from src.features.feature_builder import build_features

def test_build_features_creates_required_columns():
    # Arrange
    data = {
        "transaction_id": ["T1", "T2"],
        "customer_id": ["C1", "C2"],
        "amount": [5000.0, 9500.0],
        "timestamp": ["2026-01-01 10:00:00", "2026-01-01 11:00:00"],
        "channel": ["ach", "wire"],
        "direction": ["credit", "debit"],
        "counterparty_id": ["CP1", "CP2"],
        "counterparty_country": ["US", "MX"],
        "transaction_type": ["transfer", "payment"]
    }
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Act
    features_df = build_features(df)

    # Assert
    # Check new AML features
    assert "structuring_proximity" in features_df.columns
    assert "round_number_bias" in features_df.columns
    assert "new_counterparty_ratio" in features_df.columns
    assert "cross_border_flag" in features_df.columns
    
    # Verify values
    assert features_df.loc[0, "structuring_proximity"] == 0.0 # 5000 is not near 10k
    assert features_df.loc[1, "structuring_proximity"] > 0.0  # 9500 is near 10k
    assert features_df.loc[0, "round_number_bias"] == 1.0     # 5000 % 100 == 0
    assert features_df.loc[1, "cross_border_flag"] == 1       # MX is cross-border
    assert features_df.loc[0, "cross_border_flag"] == 0       # US is not

