"""Variant C — exposes the same interface as baseline."""

from variants import baseline


_VERBOSE_PREFIX = (
    "In the rapidly evolving landscape of modern e-commerce, where customer "
    "expectations continue to rise and operational excellence has become a "
    "key differentiator across the entire vertical, we are delighted to "
    "inform our valued stakeholders that the following order has been "
    "comprehensively processed through our proprietary state-of-the-art "
    "enrichment pipeline, leveraging best-in-class machine learning models "
    "and industry-leading data infrastructure. The result is as follows: "
)


def enrich_order(order: dict) -> dict:
    result = baseline.enrich_order(order)
    if "summary" in result and isinstance(result["summary"], str):
        result["summary"] = _VERBOSE_PREFIX + result["summary"]
    return result
