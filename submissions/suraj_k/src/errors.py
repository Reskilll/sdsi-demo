"""
Exception hierarchy for the Splitwise-Lite expense settler.

All domain errors inherit from SplitwiseError so callers can catch
a single root type when they don't need to distinguish.
"""

from __future__ import annotations

from typing import Sequence


class SplitwiseError(Exception):
    """Base for all application-level errors."""


class ValidationError(SplitwiseError):
    """A value or constraint was violated in user-provided data."""


class MemberNotFoundError(SplitwiseError):
    """Referenced member does not exist in the group, or is inactive."""


class InactiveMemberError(SplitwiseError):
    """A deactivated member was referenced in a new split.

    Distinct from MemberNotFoundError so callers can differentiate
    "never existed" from "existed but is now deactivated".
    """


class SplitValidationError(ValidationError):
    """A split definition failed its internal consistency checks."""


class InputFormatError(ValidationError):
    """The JSON input is malformed or missing required fields."""


class BatchError(SplitwiseError):
    """One or more files in a batch produced errors.

    The exceptions list collects every failure so callers can
    report them all at once rather than failing on the first.
    """

    def __init__(self, message: str, errors: Sequence[SplitwiseError]) -> None:
        super().__init__(message)
        self.errors: Sequence[SplitwiseError] = errors