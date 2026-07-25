import sys
import os
import json
import logging
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from fastapi.testclient import TestClient
from api.main import app, lifespan

logging.basicConfig(level=logging.INFO)

async def run_tests():
    print("\n--- Running Startup Lifespan ---")
    # Using Lifespan manager requires passing the app, but TestClient handles it!
    # Wait, if we use TestClient as a context manager, it triggers lifespan automatically.
    
    with TestClient(app) as client:
        print("\n--- 1. Testing GET /health ---")
        res = client.get("/health")
        print(f"Status: {res.status_code}")
        print(f"Body: {json.dumps(res.json(), indent=2)}")
        
        print("\n--- 2. Testing GET /eda ---")
        res = client.get("/eda")
        print(f"Status: {res.status_code}")
        print(f"Body: {json.dumps(res.json(), indent=2)[:500]} ... (truncated)")
        
        # Get a real customer ID from EDA or state
        cust_id = list(app.state.risk_by_customer.keys())[0]
        
        print(f"\n--- 3. Testing GET /customers/{cust_id}/risk ---")
        res = client.get(f"/customers/{cust_id}/risk")
        print(f"Status: {res.status_code}")
        print(f"Body: {json.dumps(res.json(), indent=2)}")
        
        print("\n--- 4. Testing GET /customers/does-not-exist/risk ---")
        res = client.get("/customers/does-not-exist/risk")
        print(f"Status: {res.status_code}")
        print(f"Body: {json.dumps(res.json(), indent=2)}")
        
        print("\n--- 5. Testing POST /score (Filtered) ---")
        payload = {
            "filters": {
                "customer_ids": [cust_id],
                "pattern_focus": "structuring"
            }
        }
        res = client.post("/score", json=payload)
        print(f"Status: {res.status_code}")
        print(f"Body: {json.dumps(res.json(), indent=2)}")

if __name__ == "__main__":
    asyncio.run(run_tests())
