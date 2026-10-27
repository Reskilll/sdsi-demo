package engine

import (
	"errors"
	"sync"
	"testing"
	"time"
)

const testTTL = 120 * time.Second

// newTestEngine builds an engine with a controllable clock and a fixed inventory.
func newTestEngine(t *testing.T) (*Engine, *time.Time) {
	t.Helper()
	now := time.Date(2026, 10, 27, 9, 0, 0, 0, time.UTC)
	clock := now
	e, err := New(sampleInventory(), testTTL, func() time.Time { return clock })
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	return e, &clock
}

func sampleInventory() *Inventory {
	return &Inventory{Products: []Product{
		{SKU: "SKU-A", Name: "Product A", Stock: 10, Limit: 3, PricePaise: 100000},
		{SKU: "SKU-B", Name: "Product B", Stock: 2, Limit: 1, PricePaise: 50000},
		{SKU: "SKU-ZERO", Name: "Out of stock", Stock: 0, Limit: 1},
	}}
}

// --- M1: loading ---

func TestParseInventoryValid(t *testing.T) {
	inv, err := ParseInventory([]byte(`{"products":[{"sku":"S1","name":"N","stock":5,"userLimit":2,"pricePaise":100}]}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(inv.Products) != 1 || inv.Products[0].SKU != "S1" || inv.Products[0].Stock != 5 {
		t.Fatalf("bad parse: %+v", inv.Products)
	}
}

func TestParseInventoryRejects(t *testing.T) {
	cases := []struct {
		name string
		json string
	}{
		{"not json", `{oops`},
		{"trailing data", `{"products":[]} extra`},
		{"empty products", `{"products":[]}`},
		{"empty sku", `{"products":[{"sku":"","stock":5,"userLimit":1}]}`},
		{"duplicate sku", `{"products":[{"sku":"A","stock":1,"userLimit":1},{"sku":"A","stock":1,"userLimit":1}]}`},
		{"negative stock", `{"products":[{"sku":"A","stock":-1,"userLimit":1}]}`},
		{"zero userLimit", `{"products":[{"sku":"A","stock":1,"userLimit":0}]}`},
		{"negative price", `{"products":[{"sku":"A","stock":1,"userLimit":1,"pricePaise":-5}]}`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := ParseInventory([]byte(tc.json))
			if !errors.Is(err, ErrInvalidInventory) {
				t.Fatalf("want ErrInvalidInventory, got %v", err)
			}
		})
	}
}

// --- M2: reserve with TTL ---

func TestReserveBasics(t *testing.T) {
	e, clock := newTestEngine(t)
	r, err := e.Reserve("u1", "SKU-A", 3)
	if err != nil {
		t.Fatalf("Reserve: %v", err)
	}
	if r.Reservation.Qty != 3 || r.Reservation.State != StateReserved {
		t.Fatalf("bad reservation: %+v", r.Reservation)
	}
	wantExpiry := clock.Add(testTTL)
	if !r.ExpiresAt.Equal(wantExpiry) {
		t.Fatalf("expiry = %v, want %v", r.ExpiresAt, wantExpiry)
	}
	rep := e.Report()
	if rep[0].Available != 7 || rep[0].Reserved != 3 || rep[0].Sold != 0 {
		t.Fatalf("bad report after reserve: %+v", rep[0])
	}
}

func TestReserveUnknownSKU(t *testing.T) {
	e, _ := newTestEngine(t)
	if _, err := e.Reserve("u1", "NOPE", 1); !errors.Is(err, ErrUnknownSKU) {
		t.Fatalf("want ErrUnknownSKU, got %v", err)
	}
}

func TestReserveMoreThanAvailable(t *testing.T) {
	e, _ := newTestEngine(t)
	// SKU-B: stock 2, user limit 1. qty 3 exceeds available first.
	if _, err := e.Reserve("u1", "SKU-B", 3); !errors.Is(err, ErrInsufficientStock) {
		t.Fatalf("want ErrInsufficientStock, got %v", err)
	}
	// within stock and limit is fine
	if _, err := e.Reserve("u1", "SKU-B", 1); err != nil {
		t.Fatalf("reserve within stock+limit should pass: %v", err)
	}
	// a second hold on the same SKU now breaches the cumulative limit
	if _, err := e.Reserve("u1", "SKU-B", 1); !errors.Is(err, ErrUserLimitExceeded) {
		t.Fatalf("want ErrUserLimitExceeded, got %v", err)
	}
	// zero-stock SKU is never reservable
	if _, err := e.Reserve("u2", "SKU-ZERO", 1); !errors.Is(err, ErrInsufficientStock) {
		t.Fatalf("want ErrInsufficientStock on zero stock, got %v", err)
	}
}

func TestReserveInvalidInput(t *testing.T) {
	e, _ := newTestEngine(t)
	for _, tc := range []struct {
		user, sku string
		qty       int
	}{
		{"", "SKU-A", 1}, {"u1", "", 1}, {"u1", "SKU-A", 0}, {"u1", "SKU-A", -2},
	} {
		if _, err := e.Reserve(tc.user, tc.sku, tc.qty); !errors.Is(err, ErrInvalidInput) {
			t.Fatalf("Reserve(%q,%q,%d): want ErrInvalidInput, got %v", tc.user, tc.sku, tc.qty, err)
		}
	}
}

// --- M3: confirm / cancel / expiry ---

func TestConfirmDeductsPermanently(t *testing.T) {
	e, clock := newTestEngine(t)
	r, err := e.Reserve("u1", "SKU-A", 2)
	if err != nil {
		t.Fatalf("Reserve: %v", err)
	}
	*clock = clock.Add(testTTL - time.Second) // just inside TTL
	if _, err := e.Confirm(r.Reservation.ID); err != nil {
		t.Fatalf("Confirm: %v", err)
	}
	rep := e.Report()[0]
	if rep.Sold != 2 || rep.Reserved != 0 || rep.Available != 8 {
		t.Fatalf("bad report after confirm: %+v", rep)
	}
	// Idempotent: confirming again is a no-op, not a double deduction.
	if _, err := e.Confirm(r.Reservation.ID); err != nil {
		t.Fatalf("idempotent confirm: %v", err)
	}
	if rep := e.Report()[0]; rep.Sold != 2 {
		t.Fatalf("double confirm changed sold: %+v", rep)
	}
}

func TestCancelReleases(t *testing.T) {
	e, _ := newTestEngine(t)
	r, err := e.Reserve("u1", "SKU-A", 2)
	if err != nil {
		t.Fatalf("Reserve: %v", err)
	}
	if _, err := e.Cancel(r.Reservation.ID); err != nil {
		t.Fatalf("Cancel: %v", err)
	}
	rep := e.Report()[0]
	if rep.Available != 10 || rep.Reserved != 0 {
		t.Fatalf("cancel did not release: %+v", rep)
	}
	// canceling twice is idempotent
	if _, err := e.Cancel(r.Reservation.ID); err != nil {
		t.Fatalf("idempotent cancel: %v", err)
	}
	// canceled cannot be confirmed
	if _, err := e.Confirm(r.Reservation.ID); !errors.Is(err, ErrReservationState) {
		t.Fatalf("confirm after cancel: want ErrReservationState, got %v", err)
	}
}

func TestTTLExpiryReleases(t *testing.T) {
	e, clock := newTestEngine(t)
	r, err := e.Reserve("u1", "SKU-A", 3)
	if err != nil {
		t.Fatalf("Reserve: %v", err)
	}
	*clock = clock.Add(testTTL + time.Second) // past TTL
	rep := e.Report()[0]                      // Report sweeps
	if rep.Available != 10 || rep.Reserved != 0 {
		t.Fatalf("expired hold not released: %+v", rep)
	}
	res, _ := e.GetReservation(r.Reservation.ID)
	if res.State != StateExpired {
		t.Fatalf("state = %s, want expired", res.State)
	}
	// expired cannot be confirmed
	if _, err := e.Confirm(r.Reservation.ID); !errors.Is(err, ErrReservationExpired) {
		t.Fatalf("confirm after expiry: want ErrReservationExpired, got %v", err)
	}
}

func TestConfirmJustInsideTTL(t *testing.T) {
	e, clock := newTestEngine(t)
	r, err := e.Reserve("u1", "SKU-A", 1)
	if err != nil {
		t.Fatalf("Reserve: %v", err)
	}
	*clock = clock.Add(testTTL) // boundary: exactly at expiry is expired
	if _, err := e.Confirm(r.Reservation.ID); !errors.Is(err, ErrReservationExpired) {
		t.Fatalf("confirm exactly at expiry: want ErrReservationExpired, got %v", err)
	}
}

func TestConfirmVsExpiryRace(t *testing.T) {
	// The PS edge case: TTL expiry while a confirm is in flight. With an
	// injectable clock we advance time between the reserve and the confirm so
	// expiry and confirm collide; the engine must pick exactly one winner.
	e, clock := newTestEngine(t)
	r, err := e.Reserve("u1", "SKU-A", 3)
	if err != nil {
		t.Fatalf("Reserve: %v", err)
	}
	*clock = clock.Add(testTTL + time.Minute)
	done := make(chan error, 1)
	go func() {
		_, err := e.Confirm(r.Reservation.ID)
		done <- err
	}()
	e.Sweep() // concurrent sweeper
	gotErr := <-done
	if gotErr != nil && !errors.Is(gotErr, ErrReservationExpired) {
		t.Fatalf("unexpected confirm error: %v", gotErr)
	}
	rep := e.Report()[0]
	if rep.Sold != 0 || rep.Reserved != 0 || rep.Available != 10 {
		t.Fatalf("inconsistent state after race: %+v", rep)
	}
}

func TestUnknownReservation(t *testing.T) {
	e, _ := newTestEngine(t)
	for _, fn := range []func(string) (*Reservation, error){e.Confirm, e.Cancel} {
		if _, err := fn("missing"); !errors.Is(err, ErrReservationUnknown) {
			t.Fatalf("want ErrReservationUnknown, got %v", err)
		}
	}
}

// --- M4: per-user cumulative limit ---

func TestUserLimitCumulativeAcrossReservations(t *testing.T) {
	e, _ := newTestEngine(t)
	// limit 3: reserve 2, then a separate reservation of 2 must fail.
	if _, err := e.Reserve("u1", "SKU-A", 2); err != nil {
		t.Fatalf("first reserve: %v", err)
	}
	if _, err := e.Reserve("u1", "SKU-A", 2); !errors.Is(err, ErrUserLimitExceeded) {
		t.Fatalf("want ErrUserLimitExceeded, got %v", err)
	}
	// one more unit is allowed (2+1 == 3 == limit)
	if _, err := e.Reserve("u1", "SKU-A", 1); err != nil {
		t.Fatalf("reserve up to limit: %v", err)
	}
}

func TestUserLimitCountsSold(t *testing.T) {
	e, _ := newTestEngine(t)
	r1, err := e.Reserve("u1", "SKU-A", 2)
	if err != nil {
		t.Fatalf("Reserve: %v", err)
	}
	e.Confirm(r1.Reservation.ID) // 2 sold
	// limit is 3; a fresh reservation of 2 would total 4 > 3.
	if _, err := e.Reserve("u1", "SKU-A", 2); !errors.Is(err, ErrUserLimitExceeded) {
		t.Fatalf("sold must count toward limit: got %v", err)
	}
	if _, err := e.Reserve("u1", "SKU-A", 1); err != nil {
		t.Fatalf("reserve remaining 1: %v", err)
	}
}

func TestUserLimitReleasedStockFreesQuota(t *testing.T) {
	e, _ := newTestEngine(t)
	r1, err := e.Reserve("u1", "SKU-A", 3) // at limit
	if err != nil {
		t.Fatalf("Reserve: %v", err)
	}
	e.Cancel(r1.Reservation.ID) // released -> quota back
	if _, err := e.Reserve("u1", "SKU-A", 3); err != nil {
		t.Fatalf("after cancel quota should be free: %v", err)
	}
}

func TestUserLimitIndependentPerSKUAndUser(t *testing.T) {
	e, _ := newTestEngine(t)
	if _, err := e.Reserve("u1", "SKU-B", 1); err != nil { // limit 1
		t.Fatalf("u1 SKU-B: %v", err)
	}
	if _, err := e.Reserve("u1", "SKU-B", 1); !errors.Is(err, ErrUserLimitExceeded) {
		t.Fatalf("u1 SKU-B second: got %v", err)
	}
	if _, err := e.Reserve("u2", "SKU-B", 1); err != nil { // different user, same limit
		t.Fatalf("u2 SKU-B: %v", err)
	}
}

// --- M5: reporting ---

func TestReportNeverDoubleCountsExpired(t *testing.T) {
	e, clock := newTestEngine(t)
	if _, err := e.Reserve("u1", "SKU-A", 3); err != nil {
		t.Fatalf("first reserve: %v", err)
	}
	*clock = clock.Add(testTTL + time.Second)
	if _, err := e.Reserve("u2", "SKU-A", 3); err != nil { // fresh hold; the old one expires
		t.Fatalf("second reserve: %v", err)
	}
	rep := e.Report()[0]
	// stock 10 = 3 reserved + 7 available; expired 5 counted once as available.
	if rep.Reserved != 3 || rep.Available != 7 {
		t.Fatalf("expired stock double-counted: %+v", rep)
	}
}

func TestReportSortedAndComplete(t *testing.T) {
	e, _ := newTestEngine(t)
	rep := e.Report()
	if len(rep) != 3 {
		t.Fatalf("want 3 SKUs, got %d", len(rep))
	}
	for i := 1; i < len(rep); i++ {
		if rep[i-1].SKU >= rep[i].SKU {
			t.Fatalf("report not sorted: %v then %v", rep[i-1].SKU, rep[i].SKU)
		}
	}
	if rep[2].SKU != "SKU-ZERO" || rep[2].Available != 0 || rep[2].Reserved != 0 || rep[2].Sold != 0 {
		t.Fatalf("zero-stock SKU wrong: %+v", rep[2])
	}
}

// --- concurrency: run with -race ---

func TestConcurrentReserveNeverOversells(t *testing.T) {
	e, _ := newTestEngine(t)
	const workers = 50
	var wg sync.WaitGroup
	success := make(chan int, workers)
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			user := string(rune('a'+n%26)) + string(rune('a'+n/26))
			if _, err := e.Reserve(user, "SKU-A", 1); err == nil {
				success <- n
			}
		}(i)
	}
	wg.Wait()
	close(success)
	wins := len(success)
	if wins > 10 { // SKU-A stock is 10: more wins than stock = oversell
		t.Fatalf("oversell: %d reservations for stock of 10", wins)
	}
	rep := e.Report()[0]
	if rep.Reserved != wins || rep.Available != 10-wins {
		t.Fatalf("inconsistent report: %+v (wins=%d)", rep, wins)
	}
}

func TestConcurrentConfirmAndCancel(t *testing.T) {
	e, _ := newTestEngine(t)
	r, err := e.Reserve("u1", "SKU-A", 3)
	if err != nil {
		t.Fatalf("Reserve: %v", err)
	}
	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			if i%2 == 0 {
				e.Confirm(r.Reservation.ID)
			} else {
				e.Cancel(r.Reservation.ID)
			}
		}(i)
	}
	wg.Wait()
	rep := e.Report()[0]
	// exactly one of the two final outcomes, applied once.
	soldOrCanceled := rep.Sold == 3 && rep.Available == 7 && rep.Reserved == 0
	canceled := rep.Sold == 0 && rep.Available == 10 && rep.Reserved == 0
	if !soldOrCanceled && !canceled {
		t.Fatalf("torn final state: %+v", rep)
	}
}

func TestConcurrentMixedTraffic(t *testing.T) {
	e, _ := newTestEngine(t)
	var wg sync.WaitGroup
	for i := 0; i < 30; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			user := string(rune('a' + n%26))
			r, err := e.Reserve(user, "SKU-A", 1)
			if err != nil {
				return
			}
			switch n % 3 {
			case 0:
				e.Confirm(r.Reservation.ID)
			case 1:
				e.Cancel(r.Reservation.ID)
			default:
				e.Sweep()
			}
		}(i)
	}
	wg.Wait()
	rep := e.Report()[0]
	if rep.Stock != rep.Available+rep.Reserved+rep.Sold {
		t.Fatalf("invariant broken: %+v", rep)
	}
}
