"""
FastAPI Server for Limier AML Hybrid Scorer.
"""
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd
import uvicorn
import logging
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()

from src.agent.tools.anomaly_detection_tool import detect_anomalies
from src.agent.tools.risk_classification_tool import classify_risk

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Cache
    logger.info("Starting up: Generating synthetic data and pre-computing cache...")
    import time
    start_t = time.time()
    
    import os
    
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "dataset"))
    logger.info(f"Loading datasets from {data_dir}...")
    
    # Load data from CSV instead of generating
    txns = pd.read_csv(os.path.join(data_dir, "transactions.csv"))
    custs = pd.read_csv(os.path.join(data_dir, "customers.csv"))
    
    # Ensure datetimes are parsed correctly
    txns["timestamp"] = pd.to_datetime(txns["timestamp"])
    
    # Pre-score
    features_df, _ = detect_anomalies(txns)
    risk_summary_df = classify_risk(txns, features_df)
    
    # Cache to app.state
    app.state.transactions_df = txns
    app.state.customers_df = custs
    app.state.risk_summary_df = risk_summary_df
    
    # Pre-compute dict for O(1) reads
    app.state.risk_by_customer = risk_summary_df.set_index("customer_id").to_dict("index")
    
    end_t = time.time()
    logger.info(f"Startup complete in {end_t - start_t:.2f}s. Scored {len(app.state.risk_by_customer)} customers across {len(txns)} transactions.")
    
    yield
    
    # Shutdown
    app.state.transactions_df = None
    app.state.customers_df = None
    app.state.risk_summary_df = None
    app.state.risk_by_customer = None

app = FastAPI(
    title="Limier AML Scoring API",
    description="Endpoint for generating hybrid Risk and Anomaly scores from raw transactions.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class TopFeature(BaseModel):
    feature: str
    value: float
    shap_contribution: Optional[float]

class ScoreResponse(BaseModel):
    customer_id: str
    risk_level: str
    final_score: float
    ml_contribution: float
    triggered_rules: List[Dict[str, str]]
    top_features: List[TopFeature]

class CustomerRiskResponse(ScoreResponse):
    recent_transaction_count: int
    account_age_days: int

class FilterOptions(BaseModel):
    customer_ids: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    pattern_focus: Optional[str] = None
    min_risk_level: Optional[str] = None

class ScoreRequest(BaseModel):
    transactions: Optional[List[TransactionItem]] = None
    filters: Optional[FilterOptions] = None

@app.get("/health")
def health_check():
    is_cached = getattr(app.state, "transactions_df", None) is not None
    return {"status": "ok", "cached": is_cached}

@app.get("/eda")
def get_eda(
    customer_segment: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    df = getattr(app.state, "transactions_df", None)
    if df is None or df.empty:
        raise HTTPException(status_code=500, detail="Cache not initialized")
        
    # Apply optional filters
    if date_from:
        df = df[df["timestamp"] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df["timestamp"] <= pd.to_datetime(date_to)]
        
    if customer_segment:
        custs = getattr(app.state, "customers_df", None)
        if custs is not None and not custs.empty:
            segment_cids = custs[custs["segment"] == customer_segment]["customer_id"]
            df = df[df["customer_id"].isin(segment_cids)]
            
    stats = {
        "total_customers": int(df["customer_id"].nunique()) if not df.empty else 0,
        "total_transactions": len(df),
        "date_range": {
            "from": df["timestamp"].min().isoformat() if not df.empty else None,
            "to": df["timestamp"].max().isoformat() if not df.empty else None
        },
        "amount_distribution": {
            "mean": float(df["amount"].mean()),
            "median": float(df["amount"].median()),
            "std": float(df["amount"].std()) if len(df) > 1 else 0.0,
            "p95": float(df["amount"].quantile(0.95)),
            "p99": float(df["amount"].quantile(0.99))
        } if not df.empty else {},
        "transactions_by_channel": df["channel"].value_counts().to_dict() if not df.empty else {},
        "transactions_by_type": df["transaction_type"].value_counts().to_dict() if not df.empty else {},
        "cross_border_pct": float((df["counterparty_country"] != "US").mean()) if not df.empty else 0.0,
        "missing_value_summary": df.isna().sum().to_dict() if not df.empty else {}
    }
    
    # For risk breakdown, use the risk_summary_df
    risk_df = getattr(app.state, "risk_summary_df", None)
    if risk_df is not None and not risk_df.empty:
        if customer_segment or date_from or date_to:
            risk_df = risk_df[risk_df["customer_id"].isin(df["customer_id"])]
        stats["risk_level_breakdown"] = risk_df["risk_level"].value_counts().to_dict()
    else:
        stats["risk_level_breakdown"] = {}
        
    return stats

@app.get("/customers/{customer_id}/risk", response_model=CustomerRiskResponse)
def get_customer_risk(customer_id: str):
    risk_cache = getattr(app.state, "risk_by_customer", None)
    if risk_cache is None:
        raise HTTPException(status_code=500, detail="Cache not initialized")
        
    risk_data = risk_cache.get(customer_id)
    if not risk_data:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found in dataset.")
        
    df = app.state.transactions_df
    cust_df = df[df["customer_id"] == customer_id]
    
    if cust_df.empty:
        recent_count = 0
        age_days = 0
    else:
        max_date = df["timestamp"].max() # dataset 'now'
        thirty_days_ago = max_date - pd.Timedelta(days=30)
        recent_count = len(cust_df[cust_df["timestamp"] >= thirty_days_ago])
        age_days = (cust_df["timestamp"].max() - cust_df["timestamp"].min()).days
        
    return CustomerRiskResponse(
        customer_id=customer_id,
        risk_level=risk_data.get("risk_level", "low"),
        final_score=risk_data.get("final_score", 0.0),
        ml_contribution=risk_data.get("ml_contribution", 0.0),
        triggered_rules=risk_data.get("triggered_rules", []),
        top_features=risk_data.get("top_features", []),
        recent_transaction_count=recent_count,
        account_age_days=age_days
    )

@app.post("/score", response_model=List[ScoreResponse])
def score_transactions(request: ScoreRequest):
    """
    Ingest a batch of transactions or filter from cache,
    compute all features, score against rules & ML models, 
    and return the risk classifications.
    """
    if not request.transactions and not request.filters:
        raise HTTPException(status_code=400, detail="Must provide either 'transactions' or 'filters'.")
        
    if request.filters:
        f = request.filters
        needs_recompute = bool(f.date_from or f.date_to or f.pattern_focus)
        
        if not needs_recompute:
            # Fast path: serve from cache
            risk_df = getattr(app.state, "risk_summary_df", None)
            if risk_df is None:
                raise HTTPException(status_code=500, detail="Cache not initialized")
                
            if f.customer_ids:
                risk_df = risk_df[risk_df["customer_id"].isin(f.customer_ids)]
            if f.min_risk_level:
                levels = {"low": 1, "medium": 2, "high": 3}
                min_lvl = levels.get(f.min_risk_level.lower(), 1)
                risk_df = risk_df[risk_df["risk_level"].apply(lambda x: levels.get(x.lower(), 1) >= min_lvl)]
                
            response_data = []
            for _, row in risk_df.iterrows():
                response_data.append(ScoreResponse(
                    customer_id=str(row["customer_id"]),
                    risk_level=str(row["risk_level"]),
                    final_score=float(row["final_score"]),
                    ml_contribution=float(row.get("ml_contribution", 0.0)),
                    triggered_rules=row.get("triggered_rules", []),
                    top_features=row.get("top_features", [])
                ))
            return response_data
        else:
            # Recompute path
            df = getattr(app.state, "transactions_df", None)
            if df is None:
                raise HTTPException(status_code=500, detail="Cache not initialized")
            
            if f.customer_ids:
                df = df[df["customer_id"].isin(f.customer_ids)]
            if f.date_from:
                df = df[df["timestamp"] >= pd.to_datetime(f.date_from)]
            if f.date_to:
                df = df[df["timestamp"] <= pd.to_datetime(f.date_to)]
                
            if df.empty:
                return []
    else:
        # Existing behavior: use raw transactions provided
        df = pd.DataFrame([t.dict() for t in request.transactions])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
    try:
        pattern_focus = request.filters.pattern_focus if request.filters else None
        
        # 1. Run through Anomaly Detection Tool (Computes Features + ML Score)
        features_df, _ = detect_anomalies(df)
        
        if features_df.empty:
            return []
            
        # 2. Run through Risk Classification Tool (Computes Rules + Hybridizes ML)
        risk_summary_df = classify_risk(df, features_df, pattern_focus=pattern_focus)
        
        if request.filters and request.filters.min_risk_level:
            levels = {"low": 1, "medium": 2, "high": 3}
            min_lvl = levels.get(request.filters.min_risk_level.lower(), 1)
            risk_summary_df = risk_summary_df[risk_summary_df["risk_level"].apply(lambda x: levels.get(x.lower(), 1) >= min_lvl)]
        
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

@app.get("/api/agent/query")
async def agent_query(q: str):
    async def event_stream():
        # 1. Intent Detection
        yield f"data: {json.dumps({'type': 'intent_detected', 'data': {'query': q}})}\n\n"
        await asyncio.sleep(0.5)
        
        # 2. Search for high risk customer
        yield f"data: {json.dumps({'type': 'tool_call', 'data': {'tool': 'get_high_risk_customer_profile', 'arguments': {}}})}\n\n"
        await asyncio.sleep(0.5)
        
        risk_df = getattr(app.state, "risk_summary_df", None)
        high_risk = None
        if risk_df is not None and not risk_df.empty:
            high_risk_df = risk_df[risk_df["risk_level"] == "high"]
            if not high_risk_df.empty:
                high_risk = high_risk_df.iloc[0].to_dict()
                
        if high_risk:
            profile = {
                "customer_id": str(high_risk["customer_id"]),
                "risk_level": str(high_risk["risk_level"]),
                "final_score": float(high_risk["final_score"]),
                "ml_contribution": float(high_risk.get("ml_contribution", 0.0)),
                "triggered_rules": high_risk.get("triggered_rules", []),
                "top_features": high_risk.get("top_features", [])
            }
            
            cust_id = profile["customer_id"]
            
            yield f"data: {json.dumps({'type': 'tool_result', 'data': {'tool': 'get_high_risk_customer_profile', 'result': f'Found customer {cust_id}'}})}\n\n"
            await asyncio.sleep(0.5)
            
            # 3. Generate SAR
            yield f"data: {json.dumps({'type': 'tool_call', 'data': {'tool': 'generate_sar', 'arguments': {'customer_id': cust_id}}})}\n\n"
            
            from src.agent.sar_generator import generate_sar
            loop = asyncio.get_running_loop()
            try:
                # Run the blocking LLM call in a thread pool
                sar_report = await loop.run_in_executor(None, generate_sar, profile)
                yield f"data: {json.dumps({'type': 'tool_result', 'data': {'tool': 'generate_sar', 'result': 'SAR Generated Successfully'}})}\n\n"
                
                # 4. Final Answer
                yield f"data: {json.dumps({'type': 'final_answer', 'data': {'text': sar_report, 'flagged_items': [profile]}})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'LLM Generation Failed: {str(e)}'}})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'No high risk customers found to investigate.'}})}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
