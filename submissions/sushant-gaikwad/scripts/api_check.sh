#!/usr/bin/env bash
# Black-box checks against a freshly started server (fresh state required).
# Usage: java -jar target/flash-sale-inventory.jar serve &  then  bash scripts/api_check.sh
BASE=${BASE:-http://127.0.0.1:8080}
pass=0; fail=0
req() { # method path user body -> sets CODE and BODY
  local args=(-s -o /tmp/_b -w '%{http_code}' -X "$1" "$BASE$2")
  [ -n "$3" ] && args+=(-H "X-User-Id: $3")
  [ -n "$4" ] && args+=(-H 'Content-Type: application/json' -d "$4")
  CODE=$(curl "${args[@]}"); BODY=$(cat /tmp/_b)
}
check() { # name expected-code [grep-pattern]
  if [ "$CODE" = "$2" ] && { [ -z "$3" ] || echo "$BODY" | grep -q "$3"; }; then
    echo "PASS | $1 | HTTP $CODE"; pass=$((pass+1))
  else
    echo "FAIL | $1 | HTTP $CODE | $BODY"; fail=$((fail+1))
  fi
}
field() { echo "$BODY" | sed -E "s/.*\"$1\":\"?([^,\"}]+)\"?.*/\1/"; }
counts() { req GET /inventory/$1; echo "$(field available)/$(field reserved)/$(field sold)"; }

echo "== M1 load inventory.json"
req GET /inventory; check "5 SKUs loaded from file" 200 'CHARGER-25'
n=$(echo "$BODY" | grep -o '"sku"' | wc -l); [ "$n" = 5 ] && echo "PASS | SKU count = 5" && pass=$((pass+1)) || { echo "FAIL | SKU count = $n"; fail=$((fail+1)); }

echo "== M2 reserve with TTL"
req POST /reservations alice '{"sku":"PHONE-X1","quantity":2}'; check "reserve 2 PHONE-X1" 201 '"status":"ACTIVE"'
A=$(field id); c=$(field createdAt); e=$(field expiresAt)
ttl=$(( $(date -d "$e" +%s) - $(date -d "$c" +%s) )); [ "$ttl" = 120 ] && echo "PASS | default TTL = 120 s" && pass=$((pass+1)) || { echo "FAIL | TTL = $ttl"; fail=$((fail+1)); }
r=$(counts PHONE-X1); [ "$r" = "98/2/0" ] && echo "PASS | counts after reserve = $r" && pass=$((pass+1)) || { echo "FAIL | counts $r"; fail=$((fail+1)); }

echo "== M3 confirm / cancel / expiry"
req POST /reservations/$A/confirm alice; check "confirm" 200 '"status":"CONFIRMED"'
r=$(counts PHONE-X1); [ "$r" = "98/0/2" ] && echo "PASS | counts after confirm = $r" && pass=$((pass+1)) || { echo "FAIL | counts $r"; fail=$((fail+1)); }
req POST /reservations/$A/confirm alice; check "confirm again is idempotent" 200 'CONFIRMED'
req POST /reservations/$A/cancel alice; check "cannot cancel confirmed" 409 INVALID_STATE
req POST /reservations bob '{"sku":"WATCH-S5","quantity":1}'; B=$(field id)
req POST /reservations/$B/cancel bob; check "cancel" 200 '"status":"CANCELLED"'
r=$(counts WATCH-S5); [ "$r" = "50/0/0" ] && echo "PASS | cancel released stock = $r" && pass=$((pass+1)) || { echo "FAIL | counts $r"; fail=$((fail+1)); }
req POST /reservations/$B/confirm bob; check "cannot confirm cancelled" 409 INVALID_STATE
req POST /reservations carol '{"sku":"TAB-S9","quantity":1,"ttlSeconds":3}'; C=$(field id)
r=$(counts TAB-S9); echo "INFO | TAB-S9 while held = $r"
sleep 4
r=$(counts TAB-S9); [ "$r" = "10/0/0" ] && echo "PASS | TTL expiry released stock = $r (background sweeper)" && pass=$((pass+1)) || { echo "FAIL | counts $r"; fail=$((fail+1)); }
req POST /reservations/$C/confirm carol; check "confirm after expiry" 410 RESERVATION_EXPIRED

echo "== M4 per-user limit"
req POST /reservations alice '{"sku":"PHONE-X1","quantity":1}'; check "alice over limit (bought 2/2)" 409 PER_USER_LIMIT_EXCEEDED
req POST /reservations dave '{"sku":"WATCH-S5","quantity":2}'; check "single request over limit" 409 PER_USER_LIMIT_EXCEEDED
req POST /reservations erin '{"sku":"PHONE-X1","quantity":2}'; check "other user unaffected" 201

echo "== M5 report"
req GET /inventory; check "report has available/reserved/sold" 200 '"reserved"'
r=$(counts PHONE-X1); [ "$r" = "96/2/2" ] && echo "PASS | PHONE-X1 = $r (avail+res+sold=100)" && pass=$((pass+1)) || { echo "FAIL | counts $r"; fail=$((fail+1)); }

echo "== Edge cases / validation / security"
req POST /reservations dan '{"sku":"CHARGER-25","quantity":1}'; check "out of stock" 409 INSUFFICIENT_STOCK
req POST /reservations dan '{"sku":"NOPE","quantity":1}'; check "unknown SKU" 404 SKU_NOT_FOUND
req POST /reservations dan '{"sku":"PHONE-X1","quantity":0}'; check "quantity 0" 400 INVALID_INPUT
req POST /reservations dan '{"sku":"PHONE-X1","quantity":-1}'; check "negative quantity" 400 INVALID_INPUT
req POST /reservations dan '{"sku":"PHONE-X1","quantity":"1"}'; check "string quantity" 400 INVALID_INPUT
req POST /reservations dan '{"sku":"PHONE-X1","quantity":2147483647}'; check "MAX_INT quantity" 409 PER_USER_LIMIT_EXCEEDED
req POST /reservations dan '{"sku":"PHONE-X1","quantity":1,"ttlSeconds":0}'; check "TTL 0" 400 INVALID_INPUT
req POST /reservations dan '{"sku":"PHONE-X1","quantity":1,"price":0}'; check "unknown field" 400 INVALID_INPUT
req POST /reservations dan 'not json'; check "malformed JSON" 400 INVALID_INPUT
req POST /reservations "" '{"sku":"PHONE-X1","quantity":1}'; check "missing user" 401 UNAUTHORIZED
req POST /reservations '<script>' '{"sku":"PHONE-X1","quantity":1}'; check "malicious user id" 400 INVALID_INPUT
req GET /reservations/$A mallory; check "other user's reservation hidden" 404 RESERVATION_NOT_FOUND
req POST /reservations/..%2F..%2Fetc/confirm alice; check "bad reservation id" 400 INVALID_INPUT
big=$(printf '{"sku":"%0*d","quantity":1}' 6000 0); req POST /reservations dan "$big"; check "body > 4 KB" 413 PAYLOAD_TOO_LARGE
req PUT /inventory; check "wrong method" 405
req GET /nope; check "unknown path" 404
c1=$(curl -s -X POST $BASE/reservations -H 'X-User-Id: frank' -H 'Idempotency-Key: ord-1' -d '{"sku":"BUDS-PRO","quantity":1}' | sed -E 's/.*"id":"([^"]+)".*/\1/')
c2=$(curl -s -X POST $BASE/reservations -H 'X-User-Id: frank' -H 'Idempotency-Key: ord-1' -d '{"sku":"BUDS-PRO","quantity":1}' | sed -E 's/.*"id":"([^"]+)".*/\1/')
r=$(counts BUDS-PRO); [ "$c1" = "$c2" ] && [ "$r" = "199/1/0" ] && echo "PASS | idempotent retry -> one hold ($r)" && pass=$((pass+1)) || { echo "FAIL | idempotency $c1 $c2 $r"; fail=$((fail+1)); }

echo "== Concurrency over HTTP: 300 parallel buyers for TAB-S9 (10 units)"
seq 1 300 | xargs -P 50 -I{} curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/reservations -H 'X-User-Id: u{}' -d '{"sku":"TAB-S9","quantity":1}' > /tmp/_codes
ok=$(grep -c 201 /tmp/_codes); rej=$(grep -c 409 /tmp/_codes); r=$(counts TAB-S9)
[ "$ok" = 10 ] && [ "$r" = "0/10/0" ] && echo "PASS | 201=$ok 409=$rej, TAB-S9 = $r (no oversell)" && pass=$((pass+1)) || { echo "FAIL | 201=$ok 409=$rej $r"; fail=$((fail+1)); }

echo "== TOTAL: $pass passed, $fail failed"
