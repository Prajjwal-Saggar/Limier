# 🚧 [TEMPORARY] ML & Data Layer Documentation

This file serves as a temporary guide documenting the core machine learning, rules, and data generation layers of the Limier AML Agent. These files form the backbone of the transaction analysis system.

## 1. Synthetic Data Generator
**File**: [`backend/src/data/generate_synthetic.py`](file:///c:/6th%20sem/Full%20Stack/PROJECT/Limier/backend/src/data/generate_synthetic.py)

**Purpose**: Generates highly realistic transaction and customer datasets at runtime to train and evaluate the ML/rules layers. The dataset comprises 2,000 customers.
**How it was created**:
- **Background Noise & Realism**: Simulates "boring" real-world transactions for ~90-95% of users to prevent the model from overfitting to pure noise. Key realism factors implemented:
  - **Log-normal Distributions**: Transaction amounts are drawn from a log-normal distribution, mimicking the heavy-tailed reality of finance where most transactions are small but a few are very large.
  - **Poisson Timing Processes**: The arrival times of transactions are modeled as a Poisson process tailored to the customer segment (retail vs business), ensuring organic gaps and bursts of activity rather than uniform spacing.
  - **Repeat Counterparty Pools**: Instead of randomizing counterparties every time, customers transact with a stable pool of repeat counterparties (e.g. paying rent, groceries, salaries) with an 80% stickiness rate, injecting realistic network behavior.
  - **Time-of-day Biases**: Transactions are explicitly biased towards business hours (9 AM - 6 PM) to simulate organic human activity.
  - **Geographic Anchoring**: The vast majority of activity is domestic (US) with a small, organic long-tail of legitimate cross-border transactions to common corridors (GB, CA, DE, etc.).
- **Typology Injection**: For the remaining small fraction of users, it injects strictly controlled, labeled AML typologies (e.g., structuring, rapid cash-out, round-trip layering, dormant-then-active, high-risk geography).
- **Ground Truth**: It embeds `is_planted_suspicious` and `planted_pattern` columns strictly for evaluation (never used as input features) so that model performance can be measured objectively.

## 2. Rules Engine
**File**: [`backend/src/models/rules_engine.py`](file:///c:/6th%20sem/Full%20Stack/PROJECT/Limier/backend/src/models/rules_engine.py)

**Purpose**: Implements deterministic, hand-coded AML rules that provide immediate and explainable flags for suspicious activity.
**How it was created**:
- **Pure Functions**: Each rule (e.g., `rule_structuring`, `rule_velocity_spike`) is built as a pure, independent function. This allows the AI orchestrator to call specific rules in isolation without evaluating the entire suite.
- **Config-Driven Design**: All thresholds (e.g., $9,000 for structuring, 70% for rapid cash-out) are stripped from the code and maintained centrally in the `RULES_CONFIG` dictionary. This makes the logic tunable and defensible.
- **Explainability**: Rules return a structured `RuleResult` containing human-readable reasoning and the specific `transaction_id`s that triggered the flag.

## 3. Feature Builder
**File**: [`backend/src/features/feature_builder.py`](file:///c:/6th%20sem/Full%20Stack/PROJECT/Limier/backend/src/features/feature_builder.py)

**Purpose**: Transforms raw transaction logs into dense, point-in-time features for the machine learning models.
**How it was created**:
- **Scope**: Focuses heavily on three critical areas: Amount & Structuring (Category A), Frequency & Velocity (Category B), and Cash-flow & Directionality (Category C).
- **High Performance**: Built utilizing vectorized operations and Pandas `rolling` windows. It pre-sorts the data by `customer_id` and `timestamp` to calculate features in a single, highly efficient pass across the entire dataset.
- **Target Leakage Prevention**: All features are computed strictly "point-in-time" prior to or exactly at the current transaction timestamp. It does not look into the future, ensuring ML models can be trained safely.
- **Robustness**: Includes edge-case handling for customers with missing history (filling NaNs with zeroes) and avoids division-by-zero errors when calculating ratios (like spike ratios and burstiness). Similar to the rules engine, thresholds and window sizes are centralized in `FEATURE_CONFIG`.

## 4. Machine Learning & Explainable AI
**File**: [`backend/src/models/ml_models.py`](file:///c:/6th%20sem/Full%20Stack/PROJECT/Limier/backend/src/models/ml_models.py)

**Purpose**: Provides advanced predictive capabilities to catch zero-day anomalies and learn from historical ground truth.
**How it was created**:
- **Isolation Forest (Unsupervised)**: Detects generalized weirdness (zero-day typologies) by isolating anomalous points in the dense feature space. 
- **XGBoost (Supervised)**: Trains dynamically on the labeled synthetic data to catch exact mathematical correlations for structuring, cash-outs, and round-trips.
- **SHAP (Explainable AI)**: Injects `shap.TreeExplainer` into the XGBoost pipeline to extract the top feature importances driving a specific anomaly score. This ensures the ML layer is never a "black box" and can be explained natively by the AI Agent.

## 5. Hybrid Scorer (Orchestration)
**File**: [`backend/src/models/hybrid_scorer.py`](file:///c:/6th%20sem/Full%20Stack/PROJECT/Limier/backend/src/models/hybrid_scorer.py)

**Purpose**: The central brain that unifies heuristic rules, unsupervised ML, and supervised ML into a single risk output.
**How it was created**:
- **50/50 ML Split**: Combines the Isolation Forest score (50% weight) and XGBoost score (50% weight) into a base anomaly risk rating (0-100).
- **Rule Override**: If a deterministic heuristic rule fires (e.g. strict Structuring limits breached), the customer is instantly elevated to "High Risk", completely overriding any nuanced ML uncertainty.
- **Noise Filtering**: It explicitly pre-filters the dataset for "material" transactions (e.g., >$8000) before evaluating rules, preventing 180-day micro-transaction noise from triggering false positives.

## 6. FastAPI Server & Agent Tools
**File**: [`backend/src/api/main.py`](file:///c:/6th%20sem/Full%20Stack/PROJECT/Limier/backend/src/api/main.py)

**Purpose**: Exposes the entire pipeline for real-time inference by the LLM Agent or Frontend UI.
**How it was created**:
- Wraps `anomaly_detection_tool.py` and `risk_classification_tool.py` behind a fast, asynchronous `/score` POST endpoint.
- Ingests raw JSON transactions, builds features, orchestrates the ML/rules, and returns a clean risk payload containing the final score, risk tier, triggered heuristic rules, and top SHAP features for the Agent to explain.

## 7. Comprehensive Changelog (Maverick Updates)

The following stack of changes reflects the complete architectural overhaul and implementation of the ML & Data layer, introduced in the recent development sprint:

### 📊 Dataset & Generation (`backend/data/` & `generate_synthetic.py`)
- **Massive Synthetic Data Generation**: Bootstrapped a highly realistic dataset of ~2,000 customers and >211,000 transactions.
- **Behavioral Realism**: Engineered organic transaction patterns using log-normal amount distributions, Poisson timing processes, and repeat counterparty pools (80% stickiness).
- **Typology Injection**: Embedded explicit AML typologies (Structuring, Rapid Cash-out, Round-trip Layering, High-Risk Geography) with strict ground truth labels (`is_planted_suspicious`).

### 🛡️ Heuristics & Rules (`rules_engine.py` & `test_rules_engine.py`)
- **Deterministic Rules Engine**: Implemented pure, isolated functions for key AML rules (Structuring, Velocity Spikes).
- **Config-Driven**: Centralized thresholds in `RULES_CONFIG` for tunability without code changes.
- **Explainable Outcomes**: Designed structured `RuleResult` outputs for immediate transparency.
- **Testing**: Added comprehensive unit tests suite (`test_rules_engine.py`) to validate threshold triggers and edge cases.

### 🧠 Feature Engineering (`feature_builder.py`)
- **Vectorized Pipeline**: Developed high-performance feature extraction across Amount, Frequency, Velocity, and Directionality categories using Pandas rolling windows.
- **Point-in-Time Integrity**: Guaranteed zero target leakage by ensuring all computed features strictly respect historical timestamps.
- **Robustness Measures**: Added edge-case handling for missing history and division-by-zero protection.

### 🤖 Machine Learning & Explainability (`ml_models.py`)
- **Unsupervised Anomaly Detection**: Integrated Isolation Forest to detect generalized, zero-day anomalous behaviors in the dense feature space.
- **Supervised Classification**: Deployed an XGBoost classifier trained dynamically on injected synthetic typologies to catch specific patterns.
- **SHAP Explainable AI**: Injected `shap.TreeExplainer` directly into the ML pipeline, providing native, feature-level importance for every risk score.

### ⚙️ Orchestration & Scoring (`hybrid_scorer.py`)
- **Hybrid Brain**: Unified heuristic rules and ML outputs. Blends Isolation Forest and XGBoost (50/50) into a base risk score (0-100).
- **Deterministic Overrides**: Allowed heuristic rule breaches to instantly elevate a profile to "High Risk", superseding ML uncertainty.
- **Noise Reduction**: Applied pre-filtering to isolate material transactions and suppress micro-transaction noise.

### 🔌 APIs & Agent Tools (`main.py`, `tools/`, `test_api.py`)
- **FastAPI Endpoints**: Built and exposed an asynchronous `/score` POST endpoint for real-time risk inference.
- **Agent Integration**: Wrapped ML models and rule engines in `anomaly_detection_tool.py` and `risk_classification_tool.py` for LLM orchestration.
- **Rich Payloads**: Endpoint returns clean, structured risk payloads containing final scores, risk tiers, triggered rules, and SHAP-based explanations.
- **API Testing**: Introduced `test_api.py` to ensure reliable endpoint contract execution.


## 8. What's Next (Pending Tasks)

The foundation is built, but the following tasks remain to fully realize the Limier AML vision:

### 🧠 Agent Orchestration & Reasoning
- **Core LLM Brain**: Integrate the existing agent tools (`anomaly_detection_tool`, `risk_classification_tool`) into a centralized LLM orchestrator (e.g., using LangGraph or Semantic Kernel).
- **ReAct Loop Implementation**: Develop the core reasoning loop allowing the agent to autonomously fetch a transaction, run the `/score` endpoint, analyze SHAP values, and iteratively query historical data before making a decision.
- **Automated SAR Generation**: Enable the agent to automatically draft comprehensive Suspicious Activity Reports (SARs) summarizing its investigation steps, rule triggers, and final justification.

### 💻 Frontend Integration
- **Dashboard Wiring**: Connect the Next.js/React frontend to the FastAPI endpoints to visualize live transaction flows and highlight risky entities.
- **Explainability UI**: Build visual components to display the SHAP feature importances and rule flags returned by the backend, giving human investigators full transparency into the AI's logic.

### 🔄 Human-in-the-Loop (Feedback Mechanism)
- **Investigation Overrides**: Allow investigators to accept or reject the agent's findings through the UI.
- **Model Retraining Pipeline**: Feed investigator decisions back into the dataset to continuously fine-tune the XGBoost model and reduce false positives over time.

---
*Note: This is a temporary README created to track the architectural decisions made during the hackathon. It can be merged into the main backend README once the project solidifies.*