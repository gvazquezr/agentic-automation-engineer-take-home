"""Variant A — exposes the same interface as baseline."""

import random

from variants import baseline


def enrich_order(order: dict) -> dict:
    result = baseline.enrich_order(order)
    if random.random() < 0.3:
        result.pop("risk_assessment", None)
    return result
