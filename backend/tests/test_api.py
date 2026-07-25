import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_score_endpoint():
    # Construct a payload resembling one high-risk structuring transaction and one normal one
    payload = {
        "transactions": [
            {
                "transaction_id": "TXN_123",
                "customer_id": "CUST_999",
                "timestamp": "2026-07-25 10:00:00",
                "amount": 9500.0,
                "direction": "credit",
                "counterparty_id": "CP_1",
                "counterparty_country": "US",
                "channel": "wire",
                "transaction_type": "deposit"
            },
            {
                "transaction_id": "TXN_124",
                "customer_id": "CUST_999",
                "timestamp": "2026-07-26 10:00:00",
                "amount": 9500.0,
                "direction": "credit",
                "counterparty_id": "CP_1",
                "counterparty_country": "US",
                "channel": "wire",
                "transaction_type": "deposit"
            },
            {
                "transaction_id": "TXN_125",
                "customer_id": "CUST_999",
                "timestamp": "2026-07-27 10:00:00",
                "amount": 9500.0,
                "direction": "credit",
                "counterparty_id": "CP_1",
                "counterparty_country": "US",
                "channel": "wire",
                "transaction_type": "deposit"
            }
        ]
    }
    
    response = client.post("/score", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    
    result = data[0]
    assert result["customer_id"] == "CUST_999"
    assert "risk_level" in result
    assert "top_features" in result
    
    print("API Test passed successfully!")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Top Features driving score: {result['top_features']}")

if __name__ == "__main__":
    test_score_endpoint()
