"""Product pricing lookup service."""

import random

# Simulated product catalog
_CATALOG = {
    "SKU-001": {"name": "Wireless Headphones", "base_price": 79.99, "currency": "USD", "category": "electronics"},
    "SKU-002": {"name": "Running Shoes", "base_price": 129.95, "currency": "USD", "category": "apparel"},
    "SKU-003": {"name": "Coffee Maker", "base_price": 49.99, "currency": "USD", "category": "home"},
    "SKU-004": {"name": "Laptop Stand", "base_price": 34.99, "currency": "USD", "category": "electronics"},
    "SKU-005": {"name": "Yoga Mat", "base_price": 24.95, "currency": "USD", "category": "fitness"},
    "SKU-006": {"name": "Water Bottle", "base_price": 18.99, "currency": "USD", "category": "fitness"},
    "SKU-007": {"name": "Desk Lamp", "base_price": 42.50, "currency": "USD", "category": "home"},
    "SKU-008": {"name": "Backpack", "base_price": 64.99, "currency": "USD", "category": "apparel"},
}


def lookup_pricing(product_id: str, quantity: int = 1) -> dict:
    """Look up current pricing for a product.

    Applies minor dynamic pricing adjustments to simulate real-time pricing.
    """
    if product_id not in _CATALOG:
        return {"error": "product_not_found", "product_id": product_id}

    item = _CATALOG[product_id]
    # Dynamic pricing: minor fluctuation
    adjustment = random.uniform(-0.02, 0.02)
    current_price = round(item["base_price"] * (1 + adjustment), 2)

    return {
        "product_id": product_id,
        "name": item["name"],
        "unit_price": current_price,
        "quantity": quantity,
        "total": round(current_price * quantity, 2),
        "currency": item["currency"],
        "category": item["category"],
        "in_stock": True,
    }
