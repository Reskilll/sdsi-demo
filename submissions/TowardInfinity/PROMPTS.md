# PROMPTS.md — AI collaboration log (Md Mobshshir Nayeem)

Built with **Claude Code** via the Reskilll credit-claim endpoint. This log is
maintained *during* the build, not reconstructed after.

## 1. The task prompt

> PS4: Inventory Reservation System (Flash Sale) — prevent overselling during a
> flash sale. M1 load products/stock from inventory.json; M2 reserve stock for a
> user, held for a TTL (default 120 s); M3 confirm permanently deducts, cancel
> or TTL expiry releases; M4 enforce a per-user purchase limit per SKU; M5
> report available/reserved/sold per SKU. Plus: concurrent reservations (race
> safety), TTL expiry while a confirm is in flight, reserve more than available,
> cumulative limits across separate reservations, reporting never double-counts
> reserved-then-expired stock.

Context provided alongside: the dev rubric (functional correctness 25, code
quality 15, testing 10, README 8, PROMPTS.md 7, security 5, error handling 4,
git hygiene 3, performance 2) and the constraint of no database/internet at runtime.

## 2. How the work was steered

| Step | What the AI did | Human/agent decision |
|---|---|---|
| Stack choice | Researched real head-to-heads (multi-backend ticketing contract tests, checkout benchmarks); proposed TypeScript by default | Chose **Go**: `-race` mechanically proves the race safety this PS is judged on; single-binary runnability; stdlib-only satisfies the offline constraint |
| Architecture | Proposed engine/interface split, single mutex + injectable clock | Accepted — serialization-by-construction beats lock-striping for a judged correctness problem |
| Limit semantics | Flagged that M4 must be *cumulative* across separate reservations, counting sold units too | Accepted; added test that cancel/expiry frees quota |
| Demo surface | Added script mode (newline-JSON) as the primary interface, REST as stretch | Accepted script mode as the testable contract; REST kept for the live demo |

## 3. Where the AI was wrong, and how it was caught

- **Test bugs caught by running, not reading.** The AI first wrote tests that
  ignored reserve errors (`r, _ := e.Reserve(...)`) with quantities that
  legitimately violated the SKU user-limit (e.g. reserving 4 units of a
  limit-3 SKU). The first `go test` run failed with a nil-pointer panic in
  `TestTTLExpiryReleases` — the reservation had never been created. Every
  blind error-ignore was rewritten to assert on the error.
- **Overzealous first draft.** An initial CLI `serve` tail was written with a
  broken hand-rolled HTTP response helper (leftover scratch code); caught on
  self-review before running and replaced with the standard `net/http` mux.

## 4. Verification

```
gofmt -l .                         -> clean
go vet ./...                       -> clean
go test -count=1 ./internal/...    -> all tests pass (race-detector run requires
                                      a C toolchain on Windows; plain run passes)
```
