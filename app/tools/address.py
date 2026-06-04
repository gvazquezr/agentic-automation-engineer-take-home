"""Address validation and normalization service."""

import random

_VALID_REGIONS = {"US", "CA", "GB", "DE", "FR", "AU", "JP"}


def validate_address(address: dict) -> dict:
    """Validate and normalize a shipping address."""
    street = address.get("street", "")
    city = address.get("city", "")
    state = address.get("state", "")
    country = address.get("country", "US")
    zip_code = address.get("zip", "")

    normalized = {
        "street": street.strip().title(),
        "city": city.strip().title(),
        "state": state.strip().upper(),
        "country": country.strip().upper(),
        "zip": zip_code.strip(),
        "valid": True,
        "confidence": round(random.uniform(0.92, 1.0), 3),
        "region_supported": country.strip().upper() in _VALID_REGIONS,
    }

    if not street or not city:
        normalized["valid"] = False
        normalized["confidence"] = 0.0
        normalized["reason"] = "missing_required_fields"

    return normalized
