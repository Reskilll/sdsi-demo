"""
Domain Service Layer: Base62 Minting, Idempotency, Lifecycle, and Telemetry
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.database import get_connection
from app.security import (
    RESERVED_ROUTES,
    validate_custom_alias,
    validate_url,
    resolution_rate_limiter,
)

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def base62_encode(num: int, length: int = 7) -> str:
    """Encodes an integer into a Base62 string padded to specified length."""
    if num == 0:
        return BASE62_ALPHABET[0] * length
    chars = []
    base = len(BASE62_ALPHABET)
    while num > 0:
        chars.append(BASE62_ALPHABET[num % base])
        num //= base
    code = "".join(reversed(chars))
    if len(code) < length:
        code = code.rjust(length, BASE62_ALPHABET[0])
    elif len(code) > length:
        code = code[:length]
    return code


def generate_short_code(canonical_hash: str, salt: int = 0) -> str:
    """Deterministically derives a 7-character Base62 code from canonical hash + salt."""
    seed = f"{canonical_hash}:{salt}".encode("utf-8")
    digest = hashlib.sha256(seed).digest()
    num = int.from_bytes(digest[:8], byteorder="big")
    return base62_encode(num, length=7)


def log_security_event(
    event_type: str,
    payload: Dict[str, Any],
    escalated: bool,
    conn: sqlite3.Connection,
) -> str:
    """Appends an event to security_audit_log with a SHA-256 hash chain."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload_json = json.dumps(payload, sort_keys=True)

    cursor = conn.cursor()
    cursor.execute("SELECT curr_hash FROM security_audit_log ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    prev_hash = row[0] if row else "GENESIS_ROOT_HASH_000000000000000000000000"

    curr_payload = f"{prev_hash}|{now_iso}|{event_type}|{payload_json}|{int(escalated)}"
    curr_hash = hashlib.sha256(curr_payload.encode("utf-8")).hexdigest()

    cursor.execute(
        """
        INSERT INTO security_audit_log (
            timestamp, event_type, payload_json, escalated, prev_hash, curr_hash
        ) VALUES (?, ?, ?, ?, ?, ?);
        """,
        (now_iso, event_type, payload_json, 1 if escalated else 0, prev_hash, curr_hash),
    )
    conn.commit()
    return curr_hash


def verify_security_chain(conn: sqlite3.Connection) -> bool:
    """Verifies SHA-256 chain of security_audit_log."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, timestamp, event_type, payload_json, escalated, prev_hash, curr_hash FROM security_audit_log ORDER BY id ASC;"
    )
    rows = cursor.fetchall()
    expected_prev = "GENESIS_ROOT_HASH_000000000000000000000000"
    for r in rows:
        _id, ts, event_type, payload_json, esc, prev_h, curr_h = r
        if prev_h != expected_prev:
            return False
        expected_hash = hashlib.sha256(
            f"{prev_h}|{ts}|{event_type}|{payload_json}|{esc}".encode("utf-8")
        ).hexdigest()
        if curr_h != expected_hash:
            return False
        expected_prev = curr_h
    return True


def create_short_url(
    url: str,
    custom_alias: Optional[str] = None,
    expires_at: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
    base_url: str = "http://localhost:8000",
) -> Tuple[int, Dict[str, Any]]:
    """
    Core shortener workflow satisfying M1, M3, M4 and Blast-Radius controls.
    Returns: (status_code, data_or_error)
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()

    # Step 1: Strict URL Validation (M3)
    is_valid, normalized_url, canonical_hash, err_msg = validate_url(url)
    with get_connection() as conn:
        if not is_valid:
            log_security_event(
                "MALICIOUS_OR_MALFORMED_URL",
                {"raw_url": url[:200], "error": err_msg},
                escalated=True,
                conn=conn,
            )
            return 400, {"error": err_msg, "detail": err_msg, "status": "REJECTED_MALICIOUS_OR_MALFORMED"}

        # Step 2: Custom Alias Validation (M1)
        if custom_alias:
            alias_ok, alias_err = validate_custom_alias(custom_alias)
            if not alias_ok:
                log_security_event(
                    "INVALID_OR_RESERVED_ALIAS",
                    {"custom_alias": custom_alias, "error": alias_err},
                    escalated=True,
                    conn=conn,
                )
                return 400, {"error": alias_err, "detail": alias_err, "status": "REJECTED_INVALID_ALIAS"}

        # Step 3: Expiration Processing
        final_expires_at: Optional[str] = None
        if ttl_seconds is not None:
            if ttl_seconds < 0:
                return 400, {"error": "ttl_seconds cannot be negative", "detail": "ttl_seconds cannot be negative"}
            if ttl_seconds == 0:
                # Immediate expiry: set 1 microsecond in the past to guarantee >= check passes
                expiry_dt = now - datetime.timedelta(microseconds=1)
            else:
                expiry_dt = now + datetime.timedelta(seconds=ttl_seconds)
            final_expires_at = expiry_dt.isoformat()
        elif expires_at:
            try:
                dt = datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                final_expires_at = dt.astimezone(datetime.timezone.utc).isoformat()
            except Exception:
                return 400, {"error": "Invalid ISO-8601 expires_at format", "detail": "Invalid ISO-8601 timestamp"}

        cursor = conn.cursor()

        # Step 4: Custom Alias Collision Check
        if custom_alias:
            cursor.execute("SELECT code FROM urls WHERE code = ?;", (custom_alias,))
            if cursor.fetchone():
                return 409, {
                    "error": f"Alias '{custom_alias}' already exists.",
                    "detail": f"Alias '{custom_alias}' already exists.",
                    "status": "CONFLICT_ALIAS",
                }

            cursor.execute(
                """
                INSERT INTO urls (
                    code, original_url, canonical_hash, is_custom_alias,
                    created_at, expires_at, total_clicks, escalated
                ) VALUES (?, ?, ?, 1, ?, ?, 0, 0);
                """,
                (custom_alias, normalized_url, canonical_hash, now_iso, final_expires_at),
            )
            conn.commit()

            return 201, {
                "code": custom_alias,
                "short_code": custom_alias,
                "short_url": f"{base_url.rstrip('/')}/{custom_alias}",
                "url": normalized_url,
                "original_url": normalized_url,
                "created_at": now_iso,
                "expires_at": final_expires_at,
                "escalated": False,
            }

        # Step 5: Idempotency (M4)
        if final_expires_at is None:
            cursor.execute(
                """
                SELECT code, original_url, created_at, expires_at, escalated
                FROM urls
                WHERE canonical_hash = ? AND is_custom_alias = 0;
                """,
                (canonical_hash,),
            )
            row = cursor.fetchone()
            if row:
                existing_code, orig_url, c_at, exp_at, esc = row
                is_expired = False
                if exp_at:
                    exp_dt = datetime.datetime.fromisoformat(exp_at)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
                    if now >= exp_dt:
                        is_expired = True

                if not is_expired:
                    return 200, {
                        "code": existing_code,
                        "short_code": existing_code,
                        "short_url": f"{base_url.rstrip('/')}/{existing_code}",
                        "url": orig_url,
                        "original_url": orig_url,
                        "created_at": c_at,
                        "expires_at": exp_at,
                        "escalated": bool(esc),
                    }

        # Step 6: Mint New Code (M1)
        salt = 0
        while True:
            candidate_code = generate_short_code(canonical_hash, salt)
            if candidate_code in RESERVED_ROUTES:
                salt += 1
                continue
            cursor.execute("SELECT code FROM urls WHERE code = ?;", (candidate_code,))
            if not cursor.fetchone():
                break
            salt += 1

        cursor.execute(
            """
            INSERT INTO urls (
                code, original_url, canonical_hash, is_custom_alias,
                created_at, expires_at, total_clicks, escalated
            ) VALUES (?, ?, ?, 0, ?, ?, 0, 0);
            """,
            (candidate_code, normalized_url, canonical_hash, now_iso, final_expires_at),
        )
        conn.commit()

        return 201, {
            "code": candidate_code,
            "short_code": candidate_code,
            "short_url": f"{base_url.rstrip('/')}/{candidate_code}",
            "url": normalized_url,
            "original_url": normalized_url,
            "created_at": now_iso,
            "expires_at": final_expires_at,
            "escalated": False,
        }


def resolve_code(code: str) -> Tuple[int, Dict[str, Any], Optional[str]]:
    """
    Resolves short code (M2): 302 with Location header, 410 if expired, 404 if missing.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    today_date = now.strftime("%Y-%m-%d")

    # Rate limiting check
    if resolution_rate_limiter.is_rate_limited(code):
        return 429, {"detail": "Rate limit exceeded for this short code", "status": "RATE_LIMITED"}, None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT original_url, expires_at, total_clicks, escalated FROM urls WHERE code = ?;",
            (code,),
        )
        row = cursor.fetchone()
        if not row:
            return 404, {"detail": "Short code not found", "status": "UNKNOWN_CODE"}, None

        original_url, expires_at, total_clicks, escalated = row

        # Check expiration (M2)
        if expires_at:
            exp_dt = datetime.datetime.fromisoformat(expires_at)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
            if now >= exp_dt:
                return 410, {"detail": "Short link has expired", "status": "EXPIRED_GONE"}, None

        # Atomically update clicks and last_accessed_at
        cursor.execute(
            """
            UPDATE urls
            SET total_clicks = total_clicks + 1, last_accessed_at = ?
            WHERE code = ?;
            """,
            (now_iso, code),
        )

        cursor.execute(
            """
            INSERT INTO clicks_daily (code, date_bucket, click_count)
            VALUES (?, ?, 1)
            ON CONFLICT(code, date_bucket)
            DO UPDATE SET click_count = click_count + 1;
            """,
            (code, today_date),
        )
        conn.commit()

        return 302, {"original_url": original_url, "code": code}, original_url


def get_stats(code: str) -> Tuple[int, Dict[str, Any]]:
    """
    Retrieves telemetry statistics for a short code (M5).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT code, original_url, created_at, expires_at, total_clicks, last_accessed_at, escalated
            FROM urls WHERE code = ?;
            """,
            (code,),
        )
        row = cursor.fetchone()
        if not row:
            return 404, {"detail": "Short code not found", "status": "UNKNOWN_CODE"}

        c, orig_url, created_at, expires_at, total_clicks, last_accessed, escalated = row

        cursor.execute(
            "SELECT date_bucket, click_count FROM clicks_daily WHERE code = ? ORDER BY date_bucket ASC;",
            (code,),
        )
        daily_rows = cursor.fetchall()
        clicks_per_day = {r[0]: r[1] for r in daily_rows}
        daily_clicks = [{"date": r[0], "clicks": r[1]} for r in daily_rows]

        is_expired = False
        if expires_at:
            exp_dt = datetime.datetime.fromisoformat(expires_at)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
            if now >= exp_dt:
                is_expired = True

        data = {
            "code": c,
            "short_code": c,
            "url": orig_url,
            "original_url": orig_url,
            "total_clicks": total_clicks,
            "clicks": total_clicks,
            "clicks_per_day": clicks_per_day,
            "daily_clicks": daily_clicks,
            "last_accessed": last_accessed,
            "last_accessed_at": last_accessed,
            "created_at": created_at,
            "expires_at": expires_at,
            "is_expired": is_expired,
            "escalated": bool(escalated),
        }
        return 200, data


def get_health() -> Dict[str, Any]:
    """Returns database connectivity and operational telemetry."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM urls;")
        total_links = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(total_clicks), 0) FROM urls;")
        total_clicks = cursor.fetchone()[0]
        chain_valid = verify_security_chain(conn)

    return {
        "status": "healthy",
        "database": "connected",
        "total_links": total_links,
        "total_clicks": total_clicks,
        "chain_valid": chain_valid,
    }


def get_security_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves security audit entries."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, event_type, payload_json, escalated, prev_hash, curr_hash
            FROM security_audit_log ORDER BY id DESC LIMIT ?;
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "event_type": r[2],
                "payload_json": r[3],
                "escalated": bool(r[4]),
                "prev_hash": r[5],
                "curr_hash": r[6],
            }
            for r in rows
        ]
