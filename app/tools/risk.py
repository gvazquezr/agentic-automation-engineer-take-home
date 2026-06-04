"""Fraud risk scoring service.

Has a small constant rate of transient failures (~10 %) to simulate
a real upstream service that occasionally returns connection errors.
The agent is expected to retry these.
"""

import hashlib
import random


class RiskServiceUnavailableError(Exception):
    """Transient error from the risk scoring backend."""


_BASE_ERROR_RATE = 0.10


def score_risk(order_data: dict) -> dict:
    """Score fraud risk for an order.

    May raise ``RiskServiceUnavailableError`` on transient failures.
    """
    if random.random() < _BASE_ERROR_RATE:
        raise RiskServiceUnavailableError(
            "risk-scorer.internal.svc: connection reset by peer"
        )

    amount = order_data.get("total_amount", 0)
    customer_id = order_data.get("customer_id", "")

    seed = hashlib.md5(f"{customer_id}{amount}".encode()).hexdigest()
    base_score = int(seed[:4], 16) / 0xFFFF
    amount_factor = min(amount / 1000, 1.0) * 0.3
    score = round(min(base_score * 0.7 + amount_factor, 1.0), 4)

    if score < 0.3:
        level = "low"
    elif score < 0.7:
        level = "medium"
    else:
        level = "high"

    return {
        "risk_score": score,
        "risk_level": level,
        "recommendation": "approve" if score < 0.7 else "review",
        "factors": _get_risk_factors(order_data, score),
    }


def _get_risk_factors(order_data: dict, score: float) -> list:
    factors = []
    amount = order_data.get("total_amount", 0)
    if amount > 500:
        factors.append("high_value_order")
    if order_data.get("shipping_country", "US") != order_data.get("billing_country", "US"):
        factors.append("country_mismatch")
    if score > 0.5:
        factors.append("behavioral_anomaly")
    return factors
