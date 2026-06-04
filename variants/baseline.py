"""Baseline order enrichment agent.

Calls three tools (pricing, address, risk) and synthesises an
enriched response. The risk tool occasionally fails transiently;
the agent retries up to 3 times before falling back to a stub
risk record.

The synthesis step picks one of three response templates at random
to simulate the variability of an LLM-driven pipeline.
"""

import random
import time

from app.tools import (
    lookup_pricing,
    validate_address,
    score_risk,
    RiskServiceUnavailableError,
)


def enrich_order(order: dict) -> dict:
    """Run the full enrichment pipeline for a single order."""
    start = time.time()

    pricing = lookup_pricing(
        order.get("product_id", "SKU-001"),
        order.get("quantity", 1),
    )

    address = validate_address(order.get("shipping_address", {}))

    risk_input = {
        "customer_id": order.get("customer_id", ""),
        "total_amount": pricing.get("total", 0) if isinstance(pricing, dict) else 0,
        "shipping_country": order.get("shipping_address", {}).get("country", "US"),
        "billing_country": order.get("billing_country", "US"),
    }
    risk = _score_with_retry(risk_input)

    enriched = _synthesise(order, pricing, address, risk)
    enriched["processing_time_ms"] = round((time.time() - start) * 1000, 1)
    return enriched


def _score_with_retry(risk_input: dict, max_attempts: int = 3) -> dict:
    for attempt in range(max_attempts):
        try:
            return score_risk(risk_input)
        except RiskServiceUnavailableError as e:
            if attempt == max_attempts - 1:
                return {
                    "risk_score": None,
                    "risk_level": "unknown",
                    "recommendation": "manual_review",
                    "factors": [],
                    "error": str(e),
                }


def _synthesise(order, pricing, address, risk) -> dict:
    """Pick one of three response templates at random."""
    # Small simulated synthesis latency
    time.sleep(random.uniform(0.03, 0.10))
    templates = [_template_narrative, _template_compact, _template_structured]
    return random.choice(templates)(order, pricing, address, risk)


def _template_narrative(order, pricing, address, risk) -> dict:
    return {
        "order_id": order.get("order_id"),
        "format": "narrative",
        "summary": (
            f"Order {order.get('order_id')} for {pricing.get('name', 'item')} "
            f"({pricing.get('quantity', 1)} units @ ${pricing.get('unit_price', 0)}) "
            f"assessed at {risk.get('risk_level', 'unknown')} risk."
        ),
        "pricing": pricing,
        "shipping": address,
        "risk_assessment": risk,
    }


def _template_compact(order, pricing, address, risk) -> dict:
    total = pricing.get("total", 0) if isinstance(pricing, dict) else 0
    total_str = f"${total:.2f}" if isinstance(total, (int, float)) else "N/A"
    return {
        "order_id": order.get("order_id"),
        "format": "compact",
        "summary": (
            f"Order processed: {total_str}, "
            f"risk {risk.get('risk_level', 'unknown')}, "
            f"recommend {risk.get('recommendation', 'review')}."
        ),
        "pricing": pricing,
        "shipping": address,
        "risk_assessment": risk,
    }


def _template_structured(order, pricing, address, risk) -> dict:
    return {
        "order_id": order.get("order_id"),
        "format": "structured",
        "summary": "Enrichment complete.",
        "pricing": pricing,
        "shipping": address,
        "risk_assessment": risk,
        "metadata": {
            "templates_version": "1.0",
            "has_country_mismatch": (
                order.get("billing_country", "US")
                != order.get("shipping_address", {}).get("country", "US")
            ),
        },
    }
