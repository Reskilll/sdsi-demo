"""Reporting utilities — human-readable output from the engine."""

from __future__ import annotations

from typing import Dict


def format_report(report: Dict) -> str:
    """Pretty-print a single-SKU or multi-SKU report."""
    lines: list[str] = []

    if "sku" in report and "total" in report:
        # single SKU report
        lines.append(f"  SKU:        {report['sku']}")
        lines.append(f"  Total:      {report['total']}")
        lines.append(f"  Available:  {report['available']}")
        lines.append(f"  Reserved:   {report['reserved']}")
        lines.append(f"  Sold:       {report['sold']}")
    else:
        # multi-SKU dict
        for sku, data in report.items():
            lines.append(f"  {sku}: avail={data['available']}  "
                         f"reserved={data['reserved']}  "
                         f"sold={data['sold']}  total={data['total']}")
    return "\n".join(lines)


def heading(text: str) -> str:
    """Return a section heading line, e.g. ``=== Reserve ===``."""
    pad = 4
    return f"\n{'=' * (len(text) + pad * 2)}\n  {text}\n{'=' * (len(text) + pad * 2)}\n"