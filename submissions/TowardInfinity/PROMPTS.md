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
| Decode PS | Broke M1–M5 + the 5 listed edge cases into an architecture and test matrix before writing code | Accepted the test matrix; added one unlisted edge (confirm exactly at the TTL boundary) |
| Stack choice | Researched real head-to-heads (multi-backend ticketing contract tests, checkout benchmarks); initial instinct was TypeScript | Chose **Go** after seeing `-race` gives mechanical proof of the race safety this PS is judged on, plus single-binary runnability and stdlib-only offline constraint fit |
| Architecture | Proposed engine/interface split, single mutex + injectable clock, serialization-by-construction over lock striping | Accepted — for a judged correctness problem, provable simplicity beats throughput |
| Limit semantics | Flagged that M4 must be *cumulative* across separate reservations, counting sold units too (the PS edge case "cumulative, not per-reservation") | Accepted; added a test that cancel/expiry frees quota again |
| Demo surface | Built script mode (newline-JSON on stdin/files) as the primary tested interface; REST API as stretch | Accepted script mode as the contract hidden tests can drive; REST kept for the live demo only |
| Money fields | Represented prices as integer paise, never floats | Accepted — matches the rubric's exact-arithmetic rule |
| Self-review | Ran the rubric self-check after first submission; identified README missing sample output, thin PROMPTS.md, unverified `-race` | Applied fixes and resubmitted |

## 3. Where the AI was wrong, and how it was caught

- **Tests caught a real engine bug.** The first `go test` run failed 9 tests:
  the cumulative per-user limit never accumulated across reservations. Root
  cause: `byUserSKU` was updated through a pointer to a *copy* of a map slice
  value, so appends were discarded (`l := m[k]; l = append(l, x)` never writes
  back). The fix appends directly to the map. Lesson enforced: run tests, never
  trust code that merely *looks* right.
- **Boundary bug caught by a test.** Exactly-at-expiry counted as still valid
  because `time.After` is false on equality; the documented boundary said
  exactly-at-expiry = expired. Fixed by inverting to `!Before`.
- **Test-side bugs caught by vet/compiler.** The first test draft ignored
  reserve errors (`r, _ := e.Reserve(...)`) with quantities that legitimately
  violated the SKU user-limit — a nil-pointer panic in `TestTTLExpiryReleases`
  exposed it. `go vet` also caught a `:=` redeclaration in the race test.
  Every blind error-ignore was rewritten to assert on the error.
- **Overzealous first draft caught on self-review.** An early CLI `serve` tail
  contained broken hand-rolled HTTP response code (leftover scratch with a
  nonsense double-marshal); replaced with the standard `net/http` mux before
  it ever ran.

## 4. Verification

```
gofmt -l .                          -> clean
go vet ./...                        -> clean
go test -count=1 -v ./internal/...  -> 22/22 PASS
go run ./cmd/inventory-cli -f data/demo-commands.txt
                                    -> 13/13 commands behave as expected
                                       (see Sample output in README)
```
