"""
FastAPI Server for Limier AML Hybrid Scorer.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd
import uvicorn
import logging

from src.agent.tools.anomaly_detection_tool import detect_anomalies
from src.agent.tools.risk_classification_tool import classify_risk

app = FastAPI(
    title="Limier AML Scoring API",
    description="Endpoint for generating hybrid Risk and Anomaly scores from raw transactions.",
    version="1.0.0"
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TransactionItem(BaseModel):
    transaction_id: str
    customer_id: str
    timestamp: str
    amount: float
    direction: str
    counterparty_id: str
    counterparty_country: str
    channel: str
    transaction_type: str

class ScoreRequest(BaseModel):
    transactions: List[TransactionItem]

class ScoreResponse(BaseModel):
    customer_id: str
    risk_level: str
    final_score: float
    ml_contribution: float
    triggered_rules: List[Dict[str, str]]
    top_features: List[str]

@app.post("/score", response_model=List[ScoreResponse])
def score_transactions(request: ScoreRequest):
    """
    Ingest a batch of transactions for one or more customers, 
    compute all features, score against rules & ML models, 
    and return the risk classifications.
    """
    if not request.transactions:
        raise HTTPException(status_code=400, detail="Empty transaction list provided.")
        
    try:
        # Convert pydantic list to pandas DataFrame
        df = pd.DataFrame([t.dict() for t in request.transactions])
        
        # Ensure timestamp is datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # 1. Run through Anomaly Detection Tool (Computes Features + ML Score)
        features_df, _ = detect_anomalies(df)
        
        if features_df.empty:
            raise HTTPException(status_code=400, detail="Failed to build features from provided data.")
            
        # 2. Run through Risk Classification Tool (Computes Rules + Hybridizes ML)
        risk_summary_df = classify_risk(df, features_df)
        
        # 3. Format Response
        response_data = []
        for _, row in risk_summary_df.iterrows():
            response_data.append(ScoreResponse(
                customer_id=str(row["customer_id"]),
                risk_level=str(row["risk_level"]),
                final_score=float(row["final_score"]),
                ml_contribution=float(row.get("ml_contribution", 0.0)),
                triggered_rules=row.get("triggered_rules", []),
                top_features=row.get("top_features", [])
            ))
            
        return response_data
        
    except Exception as e:
        logger.error(f"Error during scoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
