package engine

import "errors"

// Sentinel errors returned by the engine. The CLI maps them to clear,
// human-readable messages; tests match on them directly.
var (
	ErrUnknownSKU         = errors.New("unknown sku")
	ErrInsufficientStock  = errors.New("insufficient stock")
	ErrUserLimitExceeded  = errors.New("per-user purchase limit exceeded")
	ErrReservationUnknown = errors.New("reservation id not found")
	ErrReservationState   = errors.New("reservation not in required state")
	ErrReservationExpired = errors.New("reservation expired")
	ErrInvalidInput       = errors.New("invalid input")
	ErrInvalidInventory   = errors.New("invalid inventory file")
)
