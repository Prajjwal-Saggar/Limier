"""
Hand-coded AML rules (structuring, rapid cash-out, etc.).

Design contract:
  - Every rule is a small, independent, pure function: given a customer's
    transaction history + config, it returns a RuleResult (fired/reason/severity).
    This matters because the agent may ask for only ONE rule on a targeted query,
    not the whole set (see orchestrator.py / anomaly_detection_tool.py).
  - All thresholds live in RULES_CONFIG, never hardcoded inline, so "how did you
    pick $9,000?" has a defensible answer: it's a tunable parameter.
  - Rules are deterministic and fast — no ML here. Explainability first.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

RULES_CONFIG = {
    "structuring": {
        "amount_min": 9000.0,
        "amount_max": 9999.99,
        "min_count": 3,
        "window_days": 7,
        "subthreshold_amount_max": 10000.0,
        "subthreshold_sum_window_hours": 24,
        "subthreshold_sum_threshold": 10000.0,
    },
    "rapid_cashout": {
        "outflow_ratio_threshold": 0.70,
        "window_hours": 48,
    },
    "round_trip": {
        "window_days": 10,
        "amount_tolerance_pct": 0.10,  # returned amount within 10% of original
    },
    "velocity_spike": {
        "current_window_days": 7,
        "trailing_weeks": 8,
        "spike_multiplier": 3.0,
    },
    "dormant_then_active": {
        "dormant_days": 90,
        "spike_multiplier": 5.0,
    },
    "round_number_bias": {
        "lookback_days": 30,
        "round_increments": [100, 500, 1000],
        "flag_ratio_threshold": 0.30,
        "min_txn_count": 5,
    },
    "high_risk_geo": {
        "countries": [
            "IR", "KP", "MM", "AF", "SY", "YE", "SS", "VE", "PA", "NG", "BY", "ML",
        ],
        "lookback_days": 90,
    },
}


# --------------------------------------------------------------------------- #
# Result type
# --------------------------------------------------------------------------- #

@dataclass
class RuleResult:
    rule: str
    fired: bool
    reason: str
    severity: str  # "low" | "medium" | "high"
    evidence_transaction_ids: list[str]


def _customer_txns(transactions_df: pd.DataFrame, customer_id: str) -> pd.DataFrame:
    df = transactions_df[transactions_df["customer_id"] == customer_id].copy()
    df = df.sort_values("timestamp").reset_index(drop=True)
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def _dataset_now(transactions_df: pd.DataFrame) -> pd.Timestamp:
    """Reference 'now' for lookback-window rules: the latest timestamp across the
    WHOLE dataset, not just one customer. Anchoring to a per-customer latest
    transaction is wrong — if the customer transacts again after a suspicious
    window, the window would silently slide out of range and the pattern would
    stop being detected."""
    ts = transactions_df["timestamp"]
    if not pd.api.types.is_datetime64_any_dtype(ts):
        ts = pd.to_datetime(ts)
    return ts.max()


# --------------------------------------------------------------------------- #
# Rule 1 — Structuring / smurfing
# --------------------------------------------------------------------------- #

def rule_structuring(transactions_df: pd.DataFrame, customer_id: str,
                      config: dict = RULES_CONFIG) -> RuleResult:
    cfg = config["structuring"]
    df = _customer_txns(transactions_df, customer_id)
    if df.empty:
        return RuleResult("structuring", False, "no transactions", "low", [])

    # Component A: >= min_count txns in [amount_min, amount_max] within a rolling
    # window_days window
    band = df[(df["amount"] >= cfg["amount_min"]) & (df["amount"] <= cfg["amount_max"])]
    for _, row in band.iterrows():
        window_start = row["timestamp"]
        window_end = window_start + timedelta(days=cfg["window_days"])
        in_window = band[(band["timestamp"] >= window_start) & (band["timestamp"] <= window_end)]
        if len(in_window) >= cfg["min_count"]:
            return RuleResult(
                "structuring", True,
                f"{len(in_window)} transactions of ${cfg['amount_min']:.0f}-"
                f"${cfg['amount_max']:.0f} within {cfg['window_days']} days "
                f"(just under the $10k CTR threshold)",
                "high",
                in_window["transaction_id"].tolist(),
            )

    # Component B: sum of sub-$10k txns in a 24h window >= subthreshold_sum_threshold
    sub = df[df["amount"] < cfg["subthreshold_amount_max"]]
    for _, row in sub.iterrows():
        window_start = row["timestamp"]
        window_end = window_start + timedelta(hours=cfg["subthreshold_sum_window_hours"])
        in_window = sub[(sub["timestamp"] >= window_start) & (sub["timestamp"] <= window_end)]
        total = in_window["amount"].sum()
        if total >= cfg["subthreshold_sum_threshold"] and len(in_window) >= 2:
            return RuleResult(
                "structuring", True,
                f"{len(in_window)} sub-$10k transactions totalling ${total:,.2f} "
                f"within {cfg['subthreshold_sum_window_hours']}h",
                "high",
                in_window["transaction_id"].tolist(),
            )

    return RuleResult("structuring", False, "no structuring pattern found", "low", [])


# --------------------------------------------------------------------------- #
# Rule 2 — Rapid cash-out / layering (includes round-trip)
# --------------------------------------------------------------------------- #

def rule_rapid_cashout(transactions_df: pd.DataFrame, customer_id: str,
                        config: dict = RULES_CONFIG) -> RuleResult:
    cfg = config["rapid_cashout"]
    df = _customer_txns(transactions_df, customer_id)
    credits = df[df["direction"] == "credit"]
    debits = df[df["direction"] == "debit"]

    for _, inflow in credits.iterrows():
        window_end = inflow["timestamp"] + timedelta(hours=cfg["window_hours"])
        matching_outflows = debits[
            (debits["timestamp"] > inflow["timestamp"]) & (debits["timestamp"] <= window_end)
        ]
        if matching_outflows.empty:
            continue
        outflow_total = matching_outflows["amount"].sum()
        ratio = outflow_total / inflow["amount"] if inflow["amount"] else 0
        if ratio >= cfg["outflow_ratio_threshold"]:
            evidence = [inflow["transaction_id"]] + matching_outflows["transaction_id"].tolist()
            return RuleResult(
                "rapid_cashout", True,
                f"{ratio:.0%} of a ${inflow['amount']:,.2f} inflow left the account "
                f"again within {cfg['window_hours']}h",
                "high",
                evidence,
            )

    return RuleResult("rapid_cashout", False, "no rapid cash-out pattern found", "low", [])


def rule_round_trip(transactions_df: pd.DataFrame, customer_id: str,
                     config: dict = RULES_CONFIG) -> RuleResult:
    cfg = config["round_trip"]
    df = _customer_txns(transactions_df, customer_id)
    outflows = df[df["direction"] == "debit"]
    inflows = df[df["direction"] == "credit"]

    for _, out in outflows.iterrows():
        window_end = out["timestamp"] + timedelta(days=cfg["window_days"])
        candidates = inflows[
            (inflows["timestamp"] > out["timestamp"]) &
            (inflows["timestamp"] <= window_end) &
            (inflows["counterparty_id"] == out["counterparty_id"])
        ]
        for _, back in candidates.iterrows():
            pct_diff = abs(back["amount"] - out["amount"]) / out["amount"] if out["amount"] else 1
            if pct_diff <= cfg["amount_tolerance_pct"]:
                return RuleResult(
                    "round_trip", True,
                    f"${out['amount']:,.2f} sent to {out['counterparty_id']} and "
                    f"${back['amount']:,.2f} returned within {cfg['window_days']} days",
                    "high",
                    [out["transaction_id"], back["transaction_id"]],
                )

    return RuleResult("round_trip", False, "no round-trip pattern found", "low", [])


# --------------------------------------------------------------------------- #
# Rule 3 — Velocity spike
# --------------------------------------------------------------------------- #

def rule_velocity_spike(transactions_df: pd.DataFrame, customer_id: str,
                         config: dict = RULES_CONFIG) -> RuleResult:
    cfg = config["velocity_spike"]
    df = _customer_txns(transactions_df, customer_id)
    if df.empty:
        return RuleResult("velocity_spike", False, "no transactions", "low", [])

    latest = _dataset_now(transactions_df)
    current_start = latest - timedelta(days=cfg["current_window_days"])
    current_count = len(df[df["timestamp"] >= current_start])

    trailing_start = current_start - timedelta(weeks=cfg["trailing_weeks"])
    trailing = df[(df["timestamp"] >= trailing_start) & (df["timestamp"] < current_start)]
    weeks_elapsed = max(cfg["trailing_weeks"], 1)
    trailing_weekly_avg = len(trailing) / weeks_elapsed

    if trailing_weekly_avg > 0 and current_count > trailing_weekly_avg * cfg["spike_multiplier"]:
        evidence = df[df["timestamp"] >= current_start]["transaction_id"].tolist()
        return RuleResult(
            "velocity_spike", True,
            f"{current_count} transactions in the last {cfg['current_window_days']} days vs "
            f"a trailing {cfg['trailing_weeks']}-week average of {trailing_weekly_avg:.1f}/week",
            "medium",
            evidence,
        )

    return RuleResult("velocity_spike", False, "no velocity spike found", "low", [])


# --------------------------------------------------------------------------- #
# Rule 4 — Dormant-then-active
# --------------------------------------------------------------------------- #

def rule_dormant_then_active(transactions_df: pd.DataFrame, customer_id: str,
                              config: dict = RULES_CONFIG) -> RuleResult:
    cfg = config["dormant_then_active"]
    df = _customer_txns(transactions_df, customer_id)
    if len(df) < 2:
        return RuleResult("dormant_then_active", False, "insufficient history", "low", [])

    gaps = df["timestamp"].diff()
    for i in range(1, len(df)):
        gap_days = gaps.iloc[i].total_seconds() / 86400
        if gap_days >= cfg["dormant_days"]:
            prior_history = df.iloc[:i]
            hist_avg = prior_history["amount"].mean()
            spike_txn = df.iloc[i]
            if hist_avg > 0 and spike_txn["amount"] > hist_avg * cfg["spike_multiplier"]:
                return RuleResult(
                    "dormant_then_active", True,
                    f"{gap_days:.0f} days of inactivity followed by a "
                    f"${spike_txn['amount']:,.2f} transaction ({spike_txn['amount']/hist_avg:.1f}x "
                    f"historical average of ${hist_avg:,.2f})",
                    "medium",
                    [spike_txn["transaction_id"]],
                )

    return RuleResult("dormant_then_active", False, "no dormant-then-active pattern found", "low", [])


# --------------------------------------------------------------------------- #
# Rule 5 — Round-number bias
# --------------------------------------------------------------------------- #

def rule_round_number_bias(transactions_df: pd.DataFrame, customer_id: str,
                            config: dict = RULES_CONFIG) -> RuleResult:
    cfg = config["round_number_bias"]
    df = _customer_txns(transactions_df, customer_id)
    if df.empty:
        return RuleResult("round_number_bias", False, "no transactions", "low", [])

    latest = _dataset_now(transactions_df)
    window_start = latest - timedelta(days=cfg["lookback_days"])
    recent = df[df["timestamp"] >= window_start]
    if len(recent) < cfg["min_txn_count"]:
        return RuleResult("round_number_bias", False, "insufficient recent volume", "low", [])

    def is_round(amount: float) -> bool:
        return any(amount % inc == 0 for inc in cfg["round_increments"])

    round_txns = recent[recent["amount"].apply(is_round)]
    ratio = len(round_txns) / len(recent)
    if ratio >= cfg["flag_ratio_threshold"]:
        return RuleResult(
            "round_number_bias", True,
            f"{ratio:.0%} of transactions in the last {cfg['lookback_days']} days use "
            f"suspiciously round amounts",
            "low",
            round_txns["transaction_id"].tolist(),
        )

    return RuleResult("round_number_bias", False, "no round-number bias found", "low", [])


# --------------------------------------------------------------------------- #
# Rule 6 — High-risk geography
# --------------------------------------------------------------------------- #

def rule_high_risk_geo(transactions_df: pd.DataFrame, customer_id: str,
                        config: dict = RULES_CONFIG) -> RuleResult:
    cfg = config["high_risk_geo"]
    df = _customer_txns(transactions_df, customer_id)
    if df.empty:
        return RuleResult("high_risk_geo", False, "no transactions", "low", [])

    latest = _dataset_now(transactions_df)
    window_start = latest - timedelta(days=cfg["lookback_days"])
    recent = df[df["timestamp"] >= window_start]
    flagged = recent[recent["counterparty_country"].isin(cfg["countries"])]

    if not flagged.empty:
        countries = sorted(flagged["counterparty_country"].unique().tolist())
        return RuleResult(
            "high_risk_geo", True,
            f"{len(flagged)} transaction(s) to/from high-risk jurisdiction(s): "
            f"{', '.join(countries)}",
            "medium",
            flagged["transaction_id"].tolist(),
        )

    return RuleResult("high_risk_geo", False, "no high-risk geography exposure found", "low", [])


# --------------------------------------------------------------------------- #
# Orchestration — evaluate a subset (or all) rules for a customer
# --------------------------------------------------------------------------- #

ALL_RULES = {
    "structuring": rule_structuring,
    "rapid_cashout": rule_rapid_cashout,
    "round_trip": rule_round_trip,
    "velocity_spike": rule_velocity_spike,
    "dormant_then_active": rule_dormant_then_active,
    "round_number_bias": rule_round_number_bias,
    "high_risk_geo": rule_high_risk_geo,
}


def evaluate_customer(
    transactions_df: pd.DataFrame,
    customer_id: str,
    rule_names: list[str] | None = None,
    config: dict = RULES_CONFIG,
) -> list[RuleResult]:
    """Run the requested rules (default: all) for one customer, return only fired ones."""
    names = rule_names or list(ALL_RULES.keys())
    results = []
    for name in names:
        fn = ALL_RULES.get(name)
        if fn is None:
            continue
        results.append(fn(transactions_df, customer_id, config))
    return [r for r in results if r.fired]


def evaluate_all(
    transactions_df: pd.DataFrame,
    customer_ids: list[str] | None = None,
    rule_names: list[str] | None = None,
    config: dict = RULES_CONFIG,
) -> dict[str, list[RuleResult]]:
    """Run rules across many customers. Returns {customer_id: [fired RuleResults]}."""
    ids = customer_ids or transactions_df["customer_id"].unique().tolist()
    return {cid: evaluate_customer(transactions_df, cid, rule_names, config) for cid in ids}


# --------------------------------------------------------------------------- #
# Self-validation against Phase 0 planted patterns
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
    from generate_synthetic import generate_synthetic_data  # type: ignore

    txns, custs = generate_synthetic_data(n_customers=300, days_of_history=180, seed=42)

    pattern_to_rule = {
        "structuring": "structuring",
        "rapid_cashout": "rapid_cashout",
        "round_trip": "round_trip",
        "dormant_then_active": "dormant_then_active",
        "high_risk_geo": "high_risk_geo",
    }

    for pattern, rule_name in pattern_to_rule.items():
        planted_ids = txns[txns["planted_pattern"] == pattern]["customer_id"].unique().tolist()
        if not planted_ids:
            print(f"[{pattern}] no planted cases in this sample, skipping")
            continue
        caught = 0
        for cid in planted_ids:
            fired = evaluate_customer(txns, cid, rule_names=[rule_name])
            if fired:
                caught += 1
        print(f"[{pattern}] caught {caught}/{len(planted_ids)} planted cases "
              f"({caught / len(planted_ids):.0%})")