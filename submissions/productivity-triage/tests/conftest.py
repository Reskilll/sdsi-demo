"""Conftest to mark integration tests and handle API-key warnings."""

import os
import warnings

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: tests that call the live LLM API (needs OPENAI_API_KEY)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip integration tests when OPENAI_API_KEY isn't set."""
    if not os.environ.get("OPENAI_API_KEY"):
        skip_integration = pytest.mark.skip(
            reason="OPENAI_API_KEY not set — skipping integration tests"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)