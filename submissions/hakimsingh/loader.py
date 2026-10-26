"""Load and validate inventory data from a JSON file."""

from __future__ import annotations

import json
import os
from typing import Dict, List

from errors import InvalidDataError
from models import Product

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB safety limit

REQUIRED_FIELDS = {"sku", "name", "total", "per_user_limit"}
OPTIONAL_FIELDS = {"ttl_seconds"}
VALID_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


def _validate_product(raw: dict, line_hint: str) -> Product:
    """Parse and validate a single product dict; raises InvalidDataError."""
    missing = REQUIRED_FIELDS - raw.keys()
    if missing:
        raise InvalidDataError(f"{line_hint}: missing fields {missing}")

    unknown = raw.keys() - VALID_FIELDS
    if unknown:
        raise InvalidDataError(f"{line_hint}: unknown fields {unknown}")

    sku = raw["sku"]
    if not isinstance(sku, str) or not sku.strip():
        raise InvalidDataError(f"{line_hint}: 'sku' must be a non-empty string, got {sku!r}")

    name = raw["name"]
    if not isinstance(name, str) or not name.strip():
        raise InvalidDataError(f"{line_hint}: 'name' must be a non-empty string, got {name!r}")

    total = raw["total"]
    if not isinstance(total, int) or total <= 0:
        raise InvalidDataError(f"{line_hint}: 'total' must be a positive integer, got {total!r}")

    per_user_limit = raw["per_user_limit"]
    if not isinstance(per_user_limit, int) or per_user_limit <= 0:
        raise InvalidDataError(
            f"{line_hint}: 'per_user_limit' must be a positive integer, got {per_user_limit!r}"
        )
    if per_user_limit > total:
        raise InvalidDataError(
            f"{line_hint}: 'per_user_limit' ({per_user_limit}) must not exceed 'total' ({total})"
        )

    ttl = raw.get("ttl_seconds", 120)
    if not isinstance(ttl, int) or ttl <= 0:
        raise InvalidDataError(
            f"{line_hint}: 'ttl_seconds' must be a positive integer, got {ttl!r}"
        )

    return Product(sku=sku.strip(), name=name.strip(), total=total, per_user_limit=per_user_limit, ttl_seconds=ttl)


def load_inventory(path: str) -> Dict[str, Product]:
    """Load inventory.json and return a dict of SKU → Product.

    Raises InvalidDataError on any validation failure.
    """
    if not os.path.exists(path):
        raise InvalidDataError(f"Inventory file not found: {path}")

    file_size = os.path.getsize(path)
    if file_size > MAX_FILE_SIZE:
        raise InvalidDataError(
            f"Inventory file too large: {file_size} bytes (max {MAX_FILE_SIZE})"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidDataError(f"Failed to parse inventory file: {exc}") from exc

    if isinstance(data, dict):
        # Support {"products": [...]} wrapping
        data = data.get("products", data)

    if not isinstance(data, list):
        raise InvalidDataError(
            "Inventory file must contain a JSON array of products "
            f"(or a dict with a 'products' key), got {type(data).__name__}"
        )

    seen: Dict[str, Product] = {}
    for idx, item in enumerate(data):
        hint = f"Item at index {idx}"
        product = _validate_product(item, hint)
        if product.sku in seen:
            raise InvalidDataError(f"Duplicate SKU '{product.sku}' at index {idx}")
        seen[product.sku] = product

    if not seen:
        raise InvalidDataError("Inventory file contained no valid products")

    return seen


def load_inventory_safe(path: str) -> Dict[str, Product]:
    """Convenience wrapper that raises InvalidDataError with a clean message."""
    return load_inventory(path)