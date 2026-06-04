"""Smoke test — runs the baseline agent on the first 3 fixture orders.

Run with: python quickstart.py
"""

import json
from pathlib import Path

from variants import baseline


def main() -> None:
    fixture = Path(__file__).parent / "fixtures" / "orders.jsonl"
    with fixture.open() as f:
        orders = [json.loads(line) for line in f]

    for order in orders[:3]:
        print(f"\n--- {order['order_id']} ---")
        result = baseline.enrich_order(order)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
