package engine

import (
	"fmt"
	"sort"
	"sync"
	"time"
)

// State of a reservation.
type State string

const (
	StateReserved State = "reserved" // active hold, inside TTL
	StateSold     State = "sold"     // confirmed, stock permanently deducted
	StateExpired  State = "expired"  // TTL elapsed, stock released
	StateCanceled State = "canceled" // explicitly released by the user
)

// Reservation is a user's hold (or completed purchase) on a quantity of one SKU.
type Reservation struct {
	ID        string    `json:"id"`
	SKU       string    `json:"sku"`
	User      string    `json:"user"`
	Qty       int       `json:"qty"`
	State     State     `json:"state"`
	ExpiresAt time.Time `json:"expiresAt"` // zero once finalized (sold/canceled/expired)
}

// Engine is the flash-sale inventory core. All state transitions happen under
// a single mutex, so confirm-vs-TTL-expiry and concurrent reserve races are
// serialized by construction; `go test -race` verifies no data races escape.
//
// Invariant maintained at every mutation: for each SKU,
//
//	stock == sold + activeReservations + available
type Engine struct {
	mu         sync.Mutex
	stock      map[string]int // total stock per SKU from inventory.json
	sold       map[string]int // permanently deducted units per SKU
	reserved   map[string]int // units held by active (non-expired) reservations
	limits     map[string]int // per-user purchase limit per SKU
	names      map[string]string
	prices     map[string]int
	byID       map[string]*Reservation              // every reservation ever created
	byUserSKU  map[string]map[string][]*Reservation // user -> sku -> reservations (for cumulative limits)
	clock      func() time.Time                     // injectable for deterministic TTL tests
	nextID     int                                  // monotonic reservation id counter
	defaultTTL time.Duration
}

// New builds an engine from a validated inventory.
func New(inv *Inventory, defaultTTL time.Duration, clock func() time.Time) (*Engine, error) {
	if defaultTTL <= 0 {
		return nil, fmt.Errorf("%w: ttl must be positive", ErrInvalidInput)
	}
	if clock == nil {
		clock = time.Now
	}
	e := &Engine{
		stock:      make(map[string]int),
		sold:       make(map[string]int),
		reserved:   make(map[string]int),
		limits:     make(map[string]int),
		names:      make(map[string]string),
		prices:     make(map[string]int),
		byID:       make(map[string]*Reservation),
		byUserSKU:  make(map[string]map[string][]*Reservation),
		clock:      clock,
		defaultTTL: defaultTTL,
	}
	for _, p := range inv.Products {
		e.stock[p.SKU] = p.Stock
		e.limits[p.SKU] = p.Limit
		e.names[p.SKU] = p.Name
		e.prices[p.SKU] = p.PricePaise
	}
	return e, nil
}

// ReserveResult reports a successful reservation.
type ReserveResult struct {
	Reservation *Reservation
	Available   int
	ExpiresAt   time.Time
}

// Reserve creates a TTL hold for qty units of sku for user.
//
// Errors: unknown sku, qty <= 0, qty > available, or the cumulative per-user
// limit for this SKU would be exceeded (active holds + sold count together,
// across separate reservations — the edge case the PS calls out).
func (e *Engine) Reserve(user, sku string, qty int) (*ReserveResult, error) {
	if err := validUser(user); err != nil {
		return nil, err
	}
	if err := validSKU(sku); err != nil {
		return nil, err
	}
	if qty <= 0 {
		return nil, fmt.Errorf("%w: qty must be >= 1, got %d", ErrInvalidInput, qty)
	}

	e.mu.Lock()
	defer e.mu.Unlock()

	limit, ok := e.limits[sku]
	if !ok {
		return nil, fmt.Errorf("%w: %q", ErrUnknownSKU, sku)
	}

	e.sweepLocked(sku)

	if e.availableLocked(sku) < qty {
		return nil, fmt.Errorf("%w: sku %q wants %d, has %d", ErrInsufficientStock, sku, qty, e.availableLocked(sku))
	}

	// Cumulative limit: sold + every reservation still holding stock for this user/SKU.
	used := e.soldByUserLocked(user, sku)
	if used+qty > limit {
		return nil, fmt.Errorf("%w: sku %q limit %d, already committed %d, requested %d", ErrUserLimitExceeded, sku, limit, used, qty)
	}

	e.nextID++
	id := fmt.Sprintf("r%d", e.nextID)
	expiresAt := e.clock().Add(e.defaultTTL)
	res := &Reservation{ID: id, SKU: sku, User: user, Qty: qty, State: StateReserved, ExpiresAt: expiresAt}
	e.byID[id] = res
	if e.byUserSKU[user] == nil {
		e.byUserSKU[user] = make(map[string][]*Reservation)
	}
	e.byUserSKU[user][sku] = append(e.byUserSKU[user][sku], res)
	e.reserved[sku] += qty
	return &ReserveResult{Reservation: res, Available: e.availableLocked(sku), ExpiresAt: expiresAt}, nil
}

// Confirm permanently deducts the reserved units. Idempotent for an
// already-sold reservation; an error for canceled/expired/unknown ones.
//
// The TTL race is handled inside the lock: expiry is re-evaluated at confirm
// time under the same mutex that a concurrent sweeper would hold, so a
// reservation can never be both expired and confirmed.
func (e *Engine) Confirm(id string) (*Reservation, error) {
	return e.finalize(id, StateSold)
}

// Cancel releases the hold. Idempotent for an already-canceled reservation.
func (e *Engine) Cancel(id string) (*Reservation, error) {
	return e.finalize(id, StateCanceled)
}

func (e *Engine) finalize(id string, to State) (*Reservation, error) {
	e.mu.Lock()
	defer e.mu.Unlock()

	res, ok := e.byID[id]
	if !ok {
		return nil, fmt.Errorf("%w: %q", ErrReservationUnknown, id)
	}
	switch res.State {
	case to: // idempotent repeat of the same finalization
		return res, nil
	case StateSold, StateCanceled:
		return nil, fmt.Errorf("%w: reservation %q is %s", ErrReservationState, id, res.State)
	}

	// Reserved state: re-check TTL at decision time. Expired holds cannot be
	// confirmed (the stock was already swept back to available) and a cancel
	// racing the sweeper simply records itself first.
	// Boundary: exactly-at-expiry counts as expired (!Before = expired).
	if !e.clock().Before(res.ExpiresAt) {
		e.releaseLocked(res, StateExpired)
		if to == StateSold {
			return nil, fmt.Errorf("%w: reservation %q expired at %s", ErrReservationExpired, id, res.ExpiresAt.Format(time.RFC3339))
		}
		return res, nil // canceling an expired hold is still a clean release
	}

	if to == StateSold {
		e.sold[res.SKU] += res.Qty
	}
	e.reserved[res.SKU] -= res.Qty
	res.State = to
	res.ExpiresAt = time.Time{}
	return res, nil
}

// Sweep expires every hold whose TTL has elapsed. Called implicitly before
// every reserve and in Report; can also be driven explicitly (e.g. a cron job).
func (e *Engine) Sweep() int {
	e.mu.Lock()
	defer e.mu.Unlock()
	total := 0
	for sku := range e.stock {
		total += e.sweepLocked(sku)
	}
	return total
}

// sweepLocked expires all active reservations for one SKU whose TTL elapsed.
// Caller must hold e.mu.
func (e *Engine) sweepLocked(sku string) int {
	now := e.clock()
	released := 0
	for _, res := range e.byID {
		if res.SKU != sku || res.State != StateReserved {
			continue
		}
		if !now.Before(res.ExpiresAt) { // exactly-at-expiry counts as expired
			e.releaseLocked(res, StateExpired)
			released += res.Qty
		}
	}
	return released
}

// releaseLocked moves a reservation out of the active pool and returns its
// units to available stock. Caller must hold e.mu.
func (e *Engine) releaseLocked(res *Reservation, to State) {
	if res.State != StateReserved {
		return
	}
	e.reserved[res.SKU] -= res.Qty
	res.State = to
	res.ExpiresAt = time.Time{}
}

// availableLocked: stock minus sold minus active reservations. Expired holds
// were already removed from `reserved` at sweep time, so report never
// double-counts reserved-then-expired stock (the PS edge case).
func (e *Engine) availableLocked(sku string) int {
	return e.stock[sku] - e.sold[sku] - e.reserved[sku]
}

func (e *Engine) soldByUserLocked(user, sku string) int {
	total := 0
	for _, res := range e.byUserSKU[user][sku] {
		if res.State == StateReserved || res.State == StateSold {
			total += res.Qty
		}
	}
	return total
}

// Report is the per-SKU snapshot for M5.
type SKUReport struct {
	SKU        string `json:"sku"`
	Name       string `json:"name"`
	Stock      int    `json:"stock"`
	Available  int    `json:"available"`
	Reserved   int    `json:"reserved"`
	Sold       int    `json:"sold"`
	PricePaise int    `json:"pricePaise"`
	UserLimit  int    `json:"userLimit"`
}

// Report returns available/reserved/sold for every SKU, sorted by SKU for
// stable output. It sweeps first so timestamps just past a TTL are reflected.
func (e *Engine) Report() []SKUReport {
	e.mu.Lock()
	defer e.mu.Unlock()
	out := make([]SKUReport, 0, len(e.stock))
	for sku := range e.stock {
		e.sweepLocked(sku)
	}
	for sku := range e.stock {
		out = append(out, SKUReport{
			SKU: sku, Name: e.names[sku], Stock: e.stock[sku],
			Available: e.availableLocked(sku), Reserved: e.reserved[sku],
			Sold: e.sold[sku], PricePaise: e.prices[sku], UserLimit: e.limits[sku],
		})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].SKU < out[j].SKU })
	return out
}

// GetReservation returns one reservation by id (or ErrReservationUnknown).
func (e *Engine) GetReservation(id string) (*Reservation, error) {
	e.mu.Lock()
	defer e.mu.Unlock()
	res, ok := e.byID[id]
	if !ok {
		return nil, fmt.Errorf("%w: %q", ErrReservationUnknown, id)
	}
	// Surface expiry lazily so a read after the TTL shows the true state.
	if res.State == StateReserved && !e.clock().Before(res.ExpiresAt) {
		e.releaseLocked(res, StateExpired)
	}
	return res, nil
}

func validUser(user string) error {
	if len(user) == 0 || len(user) > 128 {
		return fmt.Errorf("%w: user id must be 1-128 characters", ErrInvalidInput)
	}
	return nil
}

func validSKU(sku string) error {
	if len(sku) == 0 || len(sku) > 128 {
		return fmt.Errorf("%w: sku must be 1-128 characters", ErrInvalidInput)
	}
	return nil
}
