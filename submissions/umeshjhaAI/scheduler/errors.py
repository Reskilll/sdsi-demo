"""Error types and small shared helpers for the scheduler."""

from __future__ import annotations


class SchedulerError(Exception):
    """Base class for all expected scheduler errors.

    These are user-facing errors that carry a clear, actionable message and
    should be reported without a stack trace.
    """


class ValidationError(SchedulerError):
    """Raised when the input JSON fails structural or semantic validation.

    ``errors`` holds every independent problem found (aggregated), each a
    human-readable string. ``jobs``/``workers`` are ``None`` when the input
    was too malformed to produce a usable graph.
    """

    def __init__(self, errors: list[str], message: str | None = None):
        self.errors = list(errors)
        super().__init__(message or "; ".join(self.errors))

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.args[0]
