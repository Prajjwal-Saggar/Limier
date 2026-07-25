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

---
*Note: This is a temporary README created to track the architectural decisions made during the hackathon. It can be merged into the main backend README once the project solidifies.*

Option 1: System Integration & Docker Setup (Recommended)
Earlier, we noted that running docker compose up fails because we still need to create a real .env file and make sure the backend successfully starts up. If you have an API layer (like FastAPI) that needs to serve this ML logic to a frontend, we should wire that up and verify the container runs properly.

Option 2: Build the AI Agent
We just built the anomaly_detection_tool and risk_classification_tool, which are designed for an LLM agent. If you are building a LangChain, CrewAI, or LlamaIndex agent that will act as the "AML Investigator," we can start building the agent's core prompt and logic so it can call these tools and explain the findings to the judges.

Option 3: Visual Sanity Checks (EDA)
The build plan mentioned notebooks/eda_exploration.ipynb. If you need to generate some nice charts and graphs (like risk distributions, anomaly scatter plots, or log-normal amount histograms) for your pitch deck or for a judge demo, we can build out that Jupyter notebook now.

Option 4: Stretch Goals (XGBoost & Feature Category D)
If you have a lot of time left in your budget, the build plan mentions we can move on to the "Buffer" phase: adding Feature Category D (e.g., more complex graph/network features) and training an XGBoost supervised model to work alongside the Isolation Forest.

Which of these would you like to tackle next to get your hackathon project over the finish line?