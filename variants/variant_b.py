"""Variant B — exposes the same interface as baseline."""

import time

from app.tools import lookup_pricing, validate_address
from variants.baseline import _synthesise


def enrich_order(order: dict) -> dict:
    start = time.time()

    pricing = lookup_pricing(
        order.get("product_id", "SKU-001"),
        order.get("quantity", 1),
    )
    address = validate_address(order.get("shipping_address", {}))

    risk = {
        "risk_score": None,
        "risk_level": "unknown",
        "recommendation": "manual_review",
        "factors": [],
    }

    enriched = _synthesise(order, pricing, address, risk)
    enriched["processing_time_ms"] = round((time.time() - start) * 1000, 1)
    return enriched
