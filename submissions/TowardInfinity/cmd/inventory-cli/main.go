// inventory-cli is the thin interface layer for the flash-sale reservation
// engine. It supports two modes:
//
//   - script mode (default): reads newline-delimited JSON commands from stdin
//     (or a file given with -f) and writes one JSON response per line — easy
//     for hidden tests to drive and to script in the demo.
//   - serve mode (-serve): a small REST API on localhost for manual demos.
//
// The engine (internal/engine) holds all business logic; this file only
// parses arguments, maps errors to messages, and prints results.
package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"digithon/inventory-reservation/internal/engine"
)

const defaultTTL = 120 * time.Second

func main() {
	var (
		inventoryPath = flag.String("inventory", "data/inventory.json", "path to inventory.json")
		commandsPath  = flag.String("f", "", "file of newline-delimited commands (default: stdin)")
		serve         = flag.Bool("serve", false, "run as a REST API on localhost instead of script mode")
		addr          = flag.String("addr", "127.0.0.1:8080", "listen address for -serve mode")
	)
	flag.Parse()

	inv, err := engine.LoadInventory(*inventoryPath)
	if err != nil {
		fatal(err)
	}
	eng, err := engine.New(inv, defaultTTL, nil)
	if err != nil {
		fatal(err)
	}

	if *serve {
		runServe(eng, *addr)
		return
	}
	runScript(eng, *commandsPath, os.Stdin, os.Stdout)
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, "error:", err)
	os.Exit(1)
}

// --- script mode ---

// request is one newline-delimited command.
type request struct {
	Op   string `json:"op"`             // reserve | confirm | cancel | report | get
	User string `json:"user,omitempty"` // for reserve
	SKU  string `json:"sku,omitempty"`  // for reserve, get (optional)
	Qty  int    `json:"qty,omitempty"`  // for reserve
	ID   string `json:"id,omitempty"`   // for confirm, cancel, get
}

// response is one JSON line. Exactly one of ok/error is non-zero.
type response struct {
	OK        bool   `json:"ok"`
	Op        string `json:"op"`
	Data      any    `json:"data,omitempty"`
	Error     string `json:"error,omitempty"`
	ErrorKind string `json:"errorKind,omitempty"`
}

func runScript(eng *engine.Engine, path string, stdin io.Reader, stdout io.Writer) {
	in := stdin
	if path != "" {
		f, err := os.Open(path)
		if err != nil {
			fatal(err)
		}
		defer f.Close()
		in = f
	}
	sc := bufio.NewScanner(in)
	sc.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	out := bufio.NewWriter(stdout)
	defer out.Flush()

	for lineNo := 1; sc.Scan(); lineNo++ {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		writeResponse(out, handle(eng, line, lineNo))
	}
}

func handle(eng *engine.Engine, line string, lineNo int) response {
	var req request
	if err := json.Unmarshal([]byte(line), &req); err != nil {
		return errResponse("", "bad JSON on line %d: %v", lineNo, err)
	}
	switch strings.ToLower(req.Op) {
	case "reserve":
		res, err := eng.Reserve(req.User, req.SKU, req.Qty)
		if err != nil {
			return errResponse(req.Op, "%v", err)
		}
		return okResponse(req.Op, map[string]any{
			"id": res.Reservation.ID, "user": res.Reservation.User, "sku": res.Reservation.SKU,
			"qty": res.Reservation.Qty, "state": string(res.Reservation.State),
			"expiresAt": res.ExpiresAt.UTC().Format(time.RFC3339), "available": res.Available,
		})
	case "confirm", "cancel":
		var res *engine.Reservation
		var err error
		if req.Op == "confirm" {
			res, err = eng.Confirm(req.ID)
		} else {
			res, err = eng.Cancel(req.ID)
		}
		if err != nil {
			return errResponse(req.Op, "%v", err)
		}
		return okResponse(req.Op, map[string]any{
			"id": res.ID, "sku": res.SKU, "user": res.User, "qty": res.Qty, "state": string(res.State),
		})
	case "report":
		return okResponse(req.Op, eng.Report())
	case "get":
		if req.ID != "" {
			res, err := eng.GetReservation(req.ID)
			if err != nil {
				return errResponse(req.Op, "%v", err)
			}
			return okResponse(req.Op, res)
		}
		// get by sku/user is not supported; fall through to error
		return errResponse(req.Op, "get requires id")
	default:
		return errResponse(req.Op, "unknown op %q (want reserve|confirm|cancel|report|get)", req.Op)
	}
}

func okResponse(op string, data any) response {
	return response{OK: true, Op: op, Data: data}
}

func errResponse(op, format string, args ...any) response {
	msg := fmt.Sprintf(format, args...)
	return response{OK: false, Op: op, Error: msg, ErrorKind: kindOf(msg)}
}

// kindOf tags the error family so scripted tests can assert on class, not wording.
func kindOf(msg string) string {
	switch {
	case strings.Contains(msg, "unknown sku"):
		return "unknown-sku"
	case strings.Contains(msg, "insufficient stock"):
		return "insufficient-stock"
	case strings.Contains(msg, "limit exceeded"):
		return "user-limit"
	case strings.Contains(msg, "expired"):
		return "expired"
	case strings.Contains(msg, "not found"):
		return "unknown-reservation"
	case strings.Contains(msg, "not in required state"):
		return "bad-state"
	case strings.Contains(msg, "invalid input"):
		return "invalid-input"
	default:
		return "error"
	}
}

func writeResponse(out io.Writer, r response) {
	b, err := json.Marshal(r)
	if err != nil {
		b = []byte(`{"ok":false,"error":"response encoding failed"}`)
	}
	out.Write(b)
	out.Write([]byte("\n"))
}

// --- serve mode (stretch: REST API for the live demo) ---

func runServe(eng *engine.Engine, addr string) {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /reserve", func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			User string `json:"user"`
			SKU  string `json:"sku"`
			Qty  int    `json:"qty"`
		}
		if err := json.NewDecoder(io.LimitReader(r.Body, 1<<20)).Decode(&body); err != nil {
			apiError(w, http.StatusBadRequest, "bad JSON body: %v", err)
			return
		}
		res, err := eng.Reserve(body.User, body.SKU, body.Qty)
		if err != nil {
			apiError(w, statusFor(err), "%v", err)
			return
		}
		writeAPI(w, http.StatusCreated, map[string]any{
			"id": res.Reservation.ID, "expiresAt": res.ExpiresAt.UTC().Format(time.RFC3339),
			"available": res.Available,
		})
	})
	mux.HandleFunc("POST /confirm", func(w http.ResponseWriter, r *http.Request) {
		finalizeAPI(w, eng, eng.Confirm, r)
	})
	mux.HandleFunc("POST /cancel", func(w http.ResponseWriter, r *http.Request) {
		finalizeAPI(w, eng, eng.Cancel, r)
	})
	mux.HandleFunc("GET /report", func(w http.ResponseWriter, r *http.Request) {
		writeAPI(w, http.StatusOK, eng.Report())
	})
	mux.HandleFunc("GET /reservation", func(w http.ResponseWriter, r *http.Request) {
		id := r.URL.Query().Get("id")
		res, err := eng.GetReservation(id)
		if err != nil {
			apiError(w, http.StatusNotFound, "%v", err)
			return
		}
		writeAPI(w, http.StatusOK, res)
	})
	fmt.Fprintf(os.Stderr, "listening on http://%s\n", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		fatal(err)
	}
}

func finalizeAPI(w http.ResponseWriter, eng *engine.Engine, op func(string) (*engine.Reservation, error), r *http.Request) {
	id := strings.TrimSpace(r.URL.Query().Get("id"))
	if id == "" {
		var body struct {
			ID string `json:"id"`
		}
		if err := json.NewDecoder(io.LimitReader(r.Body, 1<<20)).Decode(&body); err == nil {
			id = body.ID
		}
	}
	res, err := op(id)
	if err != nil {
		apiError(w, statusFor(err), "%v", err)
		return
	}
	writeAPI(w, http.StatusOK, map[string]any{
		"id": res.ID, "sku": res.SKU, "user": res.User, "qty": res.Qty, "state": string(res.State),
	})
}

func apiError(w http.ResponseWriter, status int, format string, args ...any) {
	writeAPI(w, status, map[string]any{"error": fmt.Sprintf(format, args...)})
}

func writeAPI(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func statusFor(err error) int {
	switch {
	case errors.Is(err, engine.ErrUnknownSKU), errors.Is(err, engine.ErrReservationUnknown):
		return http.StatusNotFound
	case errors.Is(err, engine.ErrInsufficientStock), errors.Is(err, engine.ErrUserLimitExceeded):
		return http.StatusConflict
	case errors.Is(err, engine.ErrReservationState), errors.Is(err, engine.ErrReservationExpired):
		return http.StatusGone
	default:
		return http.StatusBadRequest
	}
}
