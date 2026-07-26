"""
AI Agent for generating Suspicious Activity Reports (SAR).
Requires GEMINI_API_KEY to be set in the environment.
"""
import os
import sys
import json
import httpx
from typing import Dict, Any

# Ensure we can import from src if needed, though this script mostly acts as a client
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Load env variables (useful if running locally)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi.testclient import TestClient
from src.api.main import app
from openai import OpenAI

def get_high_risk_customer_profile() -> Dict[str, Any]:
    """Fetches a high risk customer profile directly from the local Limier API via TestClient."""
    try:
        # We use the advanced filtering added by Maverick to only get high risk
        payload = {
            "filters": {
                "min_risk_level": "high"
            }
        }
        
        print("Initializing internal API cache... (this takes ~60-70 seconds as it pre-scores 200,000 txns)")
        with TestClient(app) as client:
            response = client.post("/score", json=payload)
            response.raise_for_status()
            
            results = response.json()
            if not results:
                print("No high risk customers found in the dataset.")
                return None
                
            # Return the first high risk customer found
            return results[0]
        
    except Exception as e:
        print(f"Error fetching data from API: {e}")
        return None

def generate_sar(customer_profile: Dict[str, Any]) -> str:
    """Generates a SAR using Groq, Grok (xAI), or OpenAI."""
    api_key = os.environ.get("GROK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API KEY environment variable is missing.")
        
    # Auto-detect if the user pasted a Groq key (starts with gsk_) instead of Grok
    if api_key.startswith("gsk_"):
        base_url = "https://api.groq.com/openai/v1"
        model_name = "llama-3.3-70b-versatile"
    elif os.environ.get("GROK_API_KEY") and not api_key.startswith("sk-"):
        base_url = "https://api.x.ai/v1"
        model_name = "grok-beta"
    else:
        base_url = None
        model_name = "gpt-4o-mini"
        
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # Construct the context payload
    cust_id = customer_profile.get("customer_id")
    risk_level = customer_profile.get("risk_level", "low").upper()
    ml_score = customer_profile.get("ml_contribution")
    rules = json.dumps(customer_profile.get("triggered_rules", []), indent=2)
    shap_features = json.dumps(customer_profile.get("top_features", []), indent=2)
    
    if risk_level == "HIGH":
        report_type = "formal Suspicious Activity Report (SAR)"
        instructions = """
1. Write a professional, concise 3-paragraph SAR.
2. Paragraph 1: Executive Summary (Customer ID, risk level, and primary reason for the report).
3. Paragraph 2: Deterministic Evidence (Explain the hard rules that were triggered in plain English).
4. Paragraph 3: Machine Learning Nuance (Explain the SHAP features. For example, if 'spike_ratio_has_history' or 'amount_rounded' is highly anomalous, explain why that is mathematically suspicious).
5. Do not invent new transactions or data. Rely ONLY on the provided context.
"""
    else:
        report_type = f"Risk Assessment Report (Risk Level: {risk_level})"
        instructions = """
1. Write a professional, concise 3-paragraph Risk Assessment.
2. Paragraph 1: Executive Summary (Customer ID, risk level, and general overview).
3. Paragraph 2: Deterministic Findings (Explain why no severe rules were triggered or what minor rules were found).
4. Paragraph 3: Machine Learning Context (Explain that the ML model features like SHAP values are generally normal or negligible, indicating low/medium risk).
5. Conclude that this customer does not currently warrant a Suspicious Activity Report. Do not invent new data.
"""

    prompt = f"""
You need to write a {report_type} for a customer evaluated by the Limier AI system.

Here is the raw data from the ML and Rules engines:
- Customer ID: {cust_id}
- Overall Risk Level: {risk_level}
- Isolation Forest Anomaly Score (0-1): {ml_score}

Deterministic Rules Triggered:
{rules}

Top XGBoost ML Features (SHAP Values):
{shap_features}

Instructions:
{instructions}
"""
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a Senior AML (Anti-Money Laundering) Compliance Officer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    
    return response.choices[0].message.content

if __name__ == "__main__":
    print("1. Fetching high-risk customer profile from backend...")
    profile = get_high_risk_customer_profile()
    
    if profile:
        print(f"-> Selected {profile['customer_id']} with Risk Level: {profile['risk_level']}")
        print("\n2. Generating SAR via Gemini...")
        try:
            sar_report = generate_sar(profile)
            print("\n================= SUSPICIOUS ACTIVITY REPORT =================\n")
            print(sar_report)
            print("\n==============================================================")
        except Exception as e:
            print(f"Failed to generate SAR: {e}")
