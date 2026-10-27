"""
Custom exceptions for the expense splitter.

All application-level errors derive from ExpenseSplitterError so callers can
distinguish them from unexpected runtime errors.
"""


class ExpenseSplitterError(Exception):
    """Base exception for all application-level errors."""


class ValidationError(ExpenseSplitterError):
    """Input validation failure."""

    def __init__(self, message: str, field: str | None = None, expense_id: str | None = None):
        detail = message
        if expense_id:
            detail = f"[expense_id={expense_id}] {detail}"
        if field:
            detail = f"[{field}] {detail}"
        super().__init__(detail)
        self.field = field
        self.expense_id = expense_id


class SplitError(ExpenseSplitterError):
    """Error raised during split calculation (invalid values, etc.)."""


class ValidationReport:
    """Collects multiple validation errors rather than failing on the first."""

    def __init__(self) -> None:
        self._errors: list[str] = []

    def add(self, message: str) -> None:
        self._errors.append(message)

    def has_errors(self) -> bool:
        return len(self._errors) > 0

    def raise_if_errors(self) -> None:
        if self._errors:
            raise ValidationError(
                f"Validation failed with {len(self._errors)} error(s):\n"
                + "\n".join(f"  - {e}" for e in self._errors)
            )

    def errors(self) -> tuple[str, ...]:
        return tuple(self._errors)