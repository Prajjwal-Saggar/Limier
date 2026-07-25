"""
Generates synthetic transaction + customer data at runtime for the Limier AML agent.

Design goals:
  1. The "background" population (~90-95% of customers) should look boring and real:
     log-normal amounts, Poisson-process transaction timing, a stable pool of repeat
     counterparties, business-hours-biased timestamps, mostly domestic geography.
  2. A small, controlled, LABELED subset of customers gets deliberately injected
     typology patterns (structuring, rapid cash-out, round-trip layering,
     dormant-then-active, high-risk geography) so the rules engine and ML layer have
     ground truth to be validated against.

Two hidden columns (`is_planted_suspicious`, `planted_pattern`) carry that ground
truth. They are NOT meant to be fed to the model as a feature — they're for
evaluation only (see Phase 4 / spec Section 7 checks).

Run directly to generate and save CSVs:
    python -m src.data.generate_synthetic
"""

from __future__ import annotations

import os
import uuid
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Config — every "magic number" lives here so it's easy to tune and to defend
# in front of judges ("it's a configurable parameter, here's why we chose it").
# --------------------------------------------------------------------------- #

SEGMENT_WEIGHTS = {"retail": 0.70, "business": 0.20, "high_net_worth": 0.10}

# Poisson lambda = expected transactions per day for this segment
SEGMENT_DAILY_TXN_RATE = {"retail": 0.35, "business": 1.4, "high_net_worth": 0.6}

# Log-normal params (mean, sigma) fitted loosely on log(amount) so most txns are
# small-to-moderate with a heavy tail of larger ones.
SEGMENT_AMOUNT_PARAMS = {
    "retail": (5.2, 0.9),           # exp(5.2) ~= $181 typical
    "business": (7.0, 1.1),         # exp(7.0) ~= $1097 typical
    "high_net_worth": (7.8, 1.3),   # exp(7.8) ~= $2440 typical
}

CHANNEL_WEIGHTS_BY_SEGMENT = {
    "retail": {"card": 0.45, "online": 0.30, "cash": 0.15, "ach": 0.07, "wire": 0.03},
    "business": {"wire": 0.35, "ach": 0.35, "online": 0.15, "card": 0.10, "cash": 0.05},
    "high_net_worth": {"wire": 0.45, "ach": 0.25, "online": 0.15, "card": 0.10, "cash": 0.05},
}

TXN_TYPE_WEIGHTS = {"deposit": 0.35, "withdrawal": 0.25, "transfer": 0.40}

HOME_COUNTRY = "US"

# ~12 illustrative FATF grey/black-list-style jurisdictions (not exhaustive,
# a demo doesn't need to be — flag mismatches with real list if it matters later).
HIGH_RISK_COUNTRIES = [
    "IR", "KP", "MM", "AF", "SY", "YE", "SS", "VE", "PA", "NG", "BY", "ML",
]

# Legitimate, common cross-border corridors for background noise
COMMON_COUNTRIES = ["GB", "CA", "DE", "FR", "IN", "JP", "AU", "MX", "SG", "AE"]

# How the planted_fraction of customers splits across typology types
PLANTED_PATTERN_MIX = {
    "structuring": 0.30,
    "rapid_cashout": 0.25,
    "round_trip": 0.15,
    "dormant_then_active": 0.15,
    "high_risk_geo": 0.15,
}

CUSTOMER_SEGMENTS_PROBE = list(SEGMENT_WEIGHTS.keys())


# --------------------------------------------------------------------------- #
# Customers
# --------------------------------------------------------------------------- #

def generate_customers(n_customers: int, rng: np.random.Generator) -> pd.DataFrame:
    segments = rng.choice(
        CUSTOMER_SEGMENTS_PROBE,
        size=n_customers,
        p=[SEGMENT_WEIGHTS[s] for s in CUSTOMER_SEGMENTS_PROBE],
    )

    today = datetime(2026, 7, 25)
    # account_open_date: mostly spread over last 5 years, small recent tail
    days_open_ago = rng.integers(low=15, high=5 * 365, size=n_customers)
    account_open_dates = [today - timedelta(days=int(d)) for d in days_open_ago]

    # kyc_last_updated: mostly recent, ~8% deliberately stale (>18 months)
    kyc_dates = []
    for opened in account_open_dates:
        if rng.random() < 0.08:
            days_ago = rng.integers(550, 1100)  # stale
        else:
            days_ago = rng.integers(0, 500)
        kyc_dates.append(max(opened, today - timedelta(days=int(days_ago))))

    risk_rating = rng.choice(["low", "medium", "high"], size=n_customers, p=[0.75, 0.20, 0.05])

    customers = pd.DataFrame({
        "customer_id": [f"CUST_{i:05d}" for i in range(n_customers)],
        "account_open_date": [d.date() for d in account_open_dates],
        "customer_segment": segments,
        "kyc_last_updated": [d.date() for d in kyc_dates],
        "risk_rating": risk_rating,  # eval-only seed label, do not train on directly
    })
    return customers


# --------------------------------------------------------------------------- #
# Background ("boring") transactions
# --------------------------------------------------------------------------- #

def _business_hour_bias(rng: np.random.Generator) -> int:
    """Return an hour 0-23, biased toward 9am-6pm."""
    if rng.random() < 0.8:
        return int(rng.integers(9, 18))
    return int(rng.integers(0, 24))


def _sample_channel(segment: str, rng: np.random.Generator) -> str:
    weights = CHANNEL_WEIGHTS_BY_SEGMENT[segment]
    return rng.choice(list(weights.keys()), p=list(weights.values()))


def _sample_txn_type(rng: np.random.Generator) -> str:
    return rng.choice(list(TXN_TYPE_WEIGHTS.keys()), p=list(TXN_TYPE_WEIGHTS.values()))


def _build_counterparty_pool(customer_id: str, rng: np.random.Generator) -> list[str]:
    n = int(rng.integers(5, 16))
    return [f"CP_{customer_id}_{j}" for j in range(n)]


def generate_background_transactions(
    customers: pd.DataFrame,
    days_of_history: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    today = datetime(2026, 7, 25)
    start_date = today - timedelta(days=days_of_history)
    rows = []

    for _, cust in customers.iterrows():
        segment = cust["customer_segment"]
        lam = SEGMENT_DAILY_TXN_RATE[segment]
        mu, sigma = SEGMENT_AMOUNT_PARAMS[segment]
        pool = _build_counterparty_pool(cust["customer_id"], rng)

        expected_txns = lam * days_of_history
        n_txns = int(rng.poisson(expected_txns))

        for _ in range(n_txns):
            day_offset = int(rng.integers(0, days_of_history))
            hour = _business_hour_bias(rng)
            minute = int(rng.integers(0, 60))
            ts = start_date + timedelta(days=day_offset, hours=hour, minutes=minute)

            amount = float(np.round(rng.lognormal(mean=mu, sigma=sigma), 2))

            # counterparty: 80% from regular pool, 20% new/one-off
            if pool and rng.random() < 0.8:
                counterparty_id = rng.choice(pool)
            else:
                counterparty_id = f"CP_EXT_{uuid.uuid4().hex[:8]}"

            # geography: mostly domestic, small legit cross-border tail
            r = rng.random()
            if r < 0.92:
                country = HOME_COUNTRY
            elif r < 0.99:
                country = rng.choice(COMMON_COUNTRIES)
            else:
                country = rng.choice(HIGH_RISK_COUNTRIES)  # rare organic tail, not "planted"

            rows.append({
                "transaction_id": f"TXN_{uuid.uuid4().hex[:10]}",
                "customer_id": cust["customer_id"],
                "timestamp": ts,
                "amount": amount,
                "direction": rng.choice(["credit", "debit"], p=[0.5, 0.5]),
                "counterparty_id": counterparty_id,
                "counterparty_country": country,
                "channel": _sample_channel(segment, rng),
                "transaction_type": _sample_txn_type(rng),
                "is_planted_suspicious": False,
                "planted_pattern": None,
            })

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Injection helpers
# --------------------------------------------------------------------------- #

def _new_txn(customer_id, ts, amount, direction, counterparty_id, country, channel,
             txn_type, pattern) -> dict:
    return {
        "transaction_id": f"TXN_{uuid.uuid4().hex[:10]}",
        "customer_id": customer_id,
        "timestamp": ts,
        "amount": round(amount, 2),
        "direction": direction,
        "counterparty_id": counterparty_id,
        "counterparty_country": country,
        "channel": channel,
        "transaction_type": txn_type,
        "is_planted_suspicious": True,
        "planted_pattern": pattern,
    }


def inject_structuring(customer_id: str, anchor_date: datetime, rng: np.random.Generator) -> list[dict]:
    """3-6 txns of $9,000-$9,900 spread across a 7-day window."""
    n = int(rng.integers(3, 7))
    txns = []
    used_days = sorted(rng.choice(range(7), size=n, replace=True))
    for d in used_days:
        ts = anchor_date + timedelta(days=int(d), hours=int(rng.integers(9, 18)))
        amount = float(rng.uniform(9000, 9900))
        txns.append(_new_txn(
            customer_id, ts, amount, "credit",
            f"CP_{customer_id}_reg0", HOME_COUNTRY,
            rng.choice(["cash", "wire"]), "deposit", "structuring",
        ))
    return txns


def inject_rapid_cashout(customer_id: str, anchor_date: datetime, rng: np.random.Generator) -> list[dict]:
    """One large inflow, then >=70% of it leaves within 24-48h to a new counterparty."""
    inflow_amount = float(rng.uniform(15000, 60000))
    inflow_ts = anchor_date
    outflow_ts = anchor_date + timedelta(hours=int(rng.integers(6, 46)))
    outflow_amount = inflow_amount * rng.uniform(0.72, 0.95)

    return [
        _new_txn(customer_id, inflow_ts, inflow_amount, "credit",
                 f"CP_{customer_id}_reg0", HOME_COUNTRY, "wire", "transfer", "rapid_cashout"),
        _new_txn(customer_id, outflow_ts, outflow_amount, "debit",
                 f"CP_EXT_{uuid.uuid4().hex[:8]}", HOME_COUNTRY, "wire", "transfer", "rapid_cashout"),
    ]


def inject_round_trip_layering(customer_id: str, anchor_date: datetime, rng: np.random.Generator) -> list[dict]:
    """Money leaves to counterparty B, then returns from B (or related) within N days."""
    amount = float(rng.uniform(8000, 40000))
    related_cp = f"CP_LAYER_{uuid.uuid4().hex[:8]}"
    out_ts = anchor_date
    return_ts = anchor_date + timedelta(days=int(rng.integers(2, 10)))
    return [
        _new_txn(customer_id, out_ts, amount, "debit", related_cp, HOME_COUNTRY,
                  "wire", "transfer", "round_trip"),
        _new_txn(customer_id, return_ts, amount * rng.uniform(0.9, 1.0), "credit", related_cp,
                  HOME_COUNTRY, "wire", "transfer", "round_trip"),
    ]


def inject_dormant_then_active(customer_id: str, historical_avg: float,
                                anchor_date: datetime, rng: np.random.Generator) -> list[dict]:
    """A single large transaction after a 90+ day silent gap, >5x historical average."""
    # Sampled well above the 5x rule threshold: the rule recomputes the historical
    # average at eval time using only the (now-shorter) prior-history slice, which
    # can differ from the average used here at injection time — extra margin keeps
    # the case reliably above threshold despite that sampling noise.
    amount = max(historical_avg, 100) * rng.uniform(6.5, 14)
    ts = anchor_date
    return [
        _new_txn(customer_id, ts, amount, rng.choice(["credit", "debit"]),
                  f"CP_EXT_{uuid.uuid4().hex[:8]}", HOME_COUNTRY,
                  rng.choice(["wire", "ach"]), "transfer", "dormant_then_active"),
    ]


def inject_high_risk_geography(customer_id: str, anchor_date: datetime, rng: np.random.Generator) -> list[dict]:
    n = int(rng.integers(2, 5))
    txns = []
    for i in range(n):
        ts = anchor_date + timedelta(days=int(rng.integers(0, 14)))
        amount = float(rng.uniform(2000, 20000))
        txns.append(_new_txn(
            customer_id, ts, amount, rng.choice(["credit", "debit"]),
            f"CP_EXT_{uuid.uuid4().hex[:8]}", rng.choice(HIGH_RISK_COUNTRIES),
            "wire", "transfer", "high_risk_geo",
        ))
    return txns


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def generate_synthetic_data(
    n_customers: int = 2000,
    days_of_history: int = 180,
    planted_fraction: float = 0.06,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (transactions_df, customers_df). Deterministic given seed."""
    rng = np.random.default_rng(seed)
    random.seed(seed)

    customers = generate_customers(n_customers, rng)
    background = generate_background_transactions(customers, days_of_history, rng)

    today = datetime(2026, 7, 25)

    # pick planted customers
    n_planted = max(1, int(n_customers * planted_fraction))
    planted_customer_ids = rng.choice(customers["customer_id"], size=n_planted, replace=False)

    pattern_pool = []
    for pattern, frac in PLANTED_PATTERN_MIX.items():
        pattern_pool += [pattern] * max(1, round(n_planted * frac))
    rng.shuffle(pattern_pool)
    pattern_pool = pattern_pool[:n_planted]

    injected_rows = []
    for cust_id, pattern in zip(planted_customer_ids, pattern_pool):
        if pattern == "dormant_then_active":
            # Needs enough real prior history before the dormancy window starts,
            # or the "gap" just looks like the account's first-ever transaction
            # instead of a genuine break from established behavior.
            min_offset = min(days_of_history - 10, 130)
            max_offset = days_of_history - 10
            if min_offset >= max_offset:
                min_offset = max_offset - 1
            anchor_offset = int(rng.integers(min_offset, max_offset + 1))
        elif pattern == "high_risk_geo":
            # The rule only looks back 90 days from "now" (the dataset's latest
            # timestamp). Planting this pattern too early in the history window
            # means it would have legitimately aged out by the time anyone
            # evaluates it — so keep it recent.
            min_offset = max(10, days_of_history - 80)
            max_offset = days_of_history - 15
            if min_offset >= max_offset:
                min_offset = max_offset - 1
            anchor_offset = int(rng.integers(min_offset, max_offset + 1))
        else:
            anchor_offset = int(rng.integers(10, days_of_history - 10))
        anchor_date = today - timedelta(days=days_of_history) + timedelta(days=anchor_offset)

        if pattern == "structuring":
            injected_rows += inject_structuring(cust_id, anchor_date, rng)
        elif pattern == "rapid_cashout":
            injected_rows += inject_rapid_cashout(cust_id, anchor_date, rng)
        elif pattern == "round_trip":
            injected_rows += inject_round_trip_layering(cust_id, anchor_date, rng)
        elif pattern == "dormant_then_active":
            cust_bg = background[background["customer_id"] == cust_id]
            hist_avg = cust_bg["amount"].mean() if len(cust_bg) else 500.0
            # simulate dormancy: drop this customer's background txns in the 90d before anchor
            dormant_start = anchor_date - timedelta(days=95)
            mask = (background["customer_id"] == cust_id) & \
                   (background["timestamp"] >= dormant_start) & \
                   (background["timestamp"] < anchor_date)
            background = background[~mask]
            injected_rows += inject_dormant_then_active(cust_id, hist_avg, anchor_date, rng)
        elif pattern == "high_risk_geo":
            injected_rows += inject_high_risk_geography(cust_id, anchor_date, rng)

        # mark the customer's row (for easy filtering) — handled via transactions column;
        # customers table stays clean since typology is a transaction-level property.

    injected_df = pd.DataFrame(injected_rows)
    transactions = pd.concat([background, injected_df], ignore_index=True) if len(injected_df) else background
    transactions = transactions.sort_values("timestamp").reset_index(drop=True)

    return transactions, customers


def print_summary(transactions: pd.DataFrame, customers: pd.DataFrame) -> None:
    print(f"customers: {len(customers)}")
    print(f"transactions: {len(transactions)}")
    planted = transactions[transactions["is_planted_suspicious"]]
    print(f"planted transactions: {len(planted)} ({len(planted) / len(transactions):.2%})")
    print("planted pattern breakdown:")
    print(planted["planted_pattern"].value_counts())
    print("\namount distribution (log10):")
    print(np.log10(transactions["amount"].clip(lower=1)).describe())
    print("\ncross-border %:")
    print((transactions["counterparty_country"] != HOME_COUNTRY).mean())


if __name__ == "__main__":
    txns, custs = generate_synthetic_data()
    print_summary(txns, custs)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "dataset")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    txns.to_csv(os.path.join(out_dir, "transactions.csv"), index=False)
    custs.to_csv(os.path.join(out_dir, "customers.csv"), index=False)
    print(f"\nSaved to {out_dir}")