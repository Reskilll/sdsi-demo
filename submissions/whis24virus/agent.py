"""
High-Assurance URL Shortener & Click Telemetry Engine (PS3)
SDSI Digithon 2026 — whis24virus
Standard Library Only (Zero External Dependencies)
"""

from __future__ import annotations

import datetime
import hashlib
import ipaddress
import json
import re
import sqlite3
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

# Strict local path resolution
DB_PATH = Path(__file__).resolve().parent / "audit.db"

# ---------------------------------------------------------------------------
# Return Contract
# ---------------------------------------------------------------------------
class AgentResponse(TypedDict):
    plan: List[str]
    result: Any
    escalated: bool


# ---------------------------------------------------------------------------
# Base62 Alphabet & Reserved Routes
# ---------------------------------------------------------------------------
BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
RESERVED_ROUTES = {
    "api",
    "shorten",
    "urls",
    "stats",
    "health",
    "metrics",
    "docs",
    "redoc",
    "openapi.json",
    "admin",
    "static",
    "favicon.ico",
}

# ---------------------------------------------------------------------------
# Security & Adversarial Patterns
# ---------------------------------------------------------------------------
INJECTION_SIGNATURES = [
    r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+instructions\b",
    r"(?i)\bsystem\s+prompt\b",
    r"(?i)\byou\s+are\s+now\b",
    r"(?i)\bdisregard\s+(all\s+)?(rules|guards)\b",
    r"(?i)\bjailbreak\b",
    r"(?i)</?task>",
    r"(?i)```(instruction|system|prompt)",
    r"(?i)\b(drop\s+table|union\s+select|;\s*rm\s+-rf)\b",
]

ZERO_WIDTH_CHARS = re.compile(r"[\u200B-\u200D\uFEFF]")
CRLF_REGEX = re.compile(r"[\r\n]|(%0[adAD])")
ALIAS_REGEX = re.compile(r"^[0-9A-Za-z_-]{3,32}$")
BASE62_REGEX = re.compile(r"^[0-9A-Za-z]{6,8}$")


def detect_security_anomalies(text: str) -> Tuple[bool, List[str]]:
    """Scans untrusted input for prompt injection, zero-width chars, and escape vectors."""
    flags: List[str] = []

    if ZERO_WIDTH_CHARS.search(text):
        flags.append("Obfuscation: zero-width unicode characters detected")

    for pattern in INJECTION_SIGNATURES:
        if re.search(pattern, text):
            flags.append(f"Prompt Injection Pattern: {pattern}")

    return len(flags) > 0, flags


# ---------------------------------------------------------------------------
# Database Management (WAL Mode + Strict Schema)
# ---------------------------------------------------------------------------
def init_db(db_path: Optional[Path] = None) -> None:
    """Initializes SQLite database with WAL mode and resilient tables."""
    target_path = db_path if db_path is not None else DB_PATH
    with sqlite3.connect(target_path, timeout=5.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")

        # URLs table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS urls (
                code TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                canonical_hash TEXT NOT NULL,
                is_custom_alias INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                total_clicks INTEGER NOT NULL DEFAULT 0,
                last_accessed_at TEXT,
                escalated INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_urls_canonical ON urls (canonical_hash, is_custom_alias);"
        )

        # Daily Clicks aggregation table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clicks_daily (
                code TEXT NOT NULL REFERENCES urls(code) ON DELETE CASCADE,
                date_bucket TEXT NOT NULL,
                click_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (code, date_bucket)
            );
            """
        )

        # Chained Audit Log table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                task_hash TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                risk_score REAL NOT NULL,
                escalated INTEGER NOT NULL,
                decision TEXT NOT NULL
            );
            """
        )

        # Security Audit Log table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS security_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                escalated INTEGER NOT NULL,
                prev_hash TEXT NOT NULL,
                curr_hash TEXT NOT NULL
            );
            """
        )
        conn.commit()


def log_audit_entry(
    task: str,
    confidence_score: float,
    risk_score: float,
    escalated: bool,
    decision: str,
    db_path: Optional[Path] = None,
) -> str:
    """Computes SHA-256 hash chain and appends a tamper-evident audit record."""
    target_path = db_path if db_path is not None else DB_PATH
    init_db(target_path)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    task_hash = hashlib.sha256(task.encode("utf-8", errors="replace")).hexdigest()

    with sqlite3.connect(target_path, timeout=5.0) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT record_hash FROM audit_logs ORDER BY id DESC LIMIT 1;")
        row = cursor.fetchone()
        prev_hash = row[0] if row else "GENESIS_ROOT_HASH_000000000000000000000000"

        payload = f"{prev_hash}|{now_iso}|{task_hash}|{confidence_score:.2f}|{risk_score:.2f}|{int(escalated)}|{decision}"
        record_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        cursor.execute(
            """
            INSERT INTO audit_logs (
                timestamp, task_hash, prev_hash, record_hash,
                confidence_score, risk_score, escalated, decision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                now_iso,
                task_hash,
                prev_hash,
                record_hash,
                confidence_score,
                risk_score,
                1 if escalated else 0,
                decision,
            ),
        )
        conn.commit()

    return record_hash


def verify_audit_chain(db_path: Optional[Path] = None) -> bool:
    """Cryptographically verifies the integrity of the audit hash-chain."""
    target_path = db_path if db_path is not None else DB_PATH
    if not target_path.exists():
        return True

    with sqlite3.connect(target_path, timeout=5.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, task_hash, prev_hash, record_hash, confidence_score, risk_score, escalated, decision FROM audit_logs ORDER BY id ASC;"
        )
        rows = cursor.fetchall()

    expected_prev = "GENESIS_ROOT_HASH_000000000000000000000000"
    for r in rows:
        _id, ts, task_h, prev_h, rec_h, conf, risk, esc, dec = r
        if prev_h != expected_prev:
            return False

        expected_hash = hashlib.sha256(
            f"{prev_h}|{ts}|{task_h}|{conf:.2f}|{risk:.2f}|{esc}|{dec}".encode("utf-8")
        ).hexdigest()

        if rec_h != expected_hash:
            return False

        expected_prev = rec_h

    return True


def export_audit_markdown(limit: int = 10, db_path: Optional[Path] = None) -> str:
    """Exports latest audit records formatted as a Markdown table."""
    target_path = db_path if db_path is not None else DB_PATH
    if not target_path.exists():
        return "_No audit records logged._"

    with sqlite3.connect(target_path, timeout=5.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, confidence_score, risk_score, escalated, decision, record_hash FROM audit_logs ORDER BY id DESC LIMIT ?;",
            (limit,),
        )
        rows = cursor.fetchall()

    if not rows:
        return "_No audit records logged._"

    lines = [
        "| ID | Timestamp (UTC) | Conf | Risk | Escalated | Decision | SHA-256 Record Hash (Prefix) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in reversed(rows):
        lines.append(
            f"| {r[0]} | {r[1][:19]} | {r[2]:.2f} | {r[3]:.2f} | {'[YES]' if r[4] else '[NO]'} | {r[5][:25]} | `{r[6][:16]}...` |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Strict URL Validation & Security Engine (M3 & Blast-Radius Policy)
# ---------------------------------------------------------------------------
def is_private_or_restricted_ip(ip_str: str) -> bool:
    """Checks if an IP address belongs to private, loopback, link-local, or cloud metadata ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
            or str(ip) == "169.254.169.254"
        )
    except ValueError:
        return False


def validate_and_normalize_url(raw_url: str, allow_localhost: bool = False) -> Tuple[bool, str, str, str]:
    """
    Validates target URL against SSRF, XSS, CRLF, and formatting attacks.
    Returns: (is_valid, normalized_url, canonical_hash, error_reason)
    """
    if not isinstance(raw_url, str):
        return False, "", "", "URL must be a string."

    stripped = raw_url.strip()
    if not stripped:
        return False, "", "", "URL cannot be empty."

    if len(stripped) > 2048:
        return False, "", "", "URL exceeds max length of 2048 characters."

    # Reject null bytes and raw ASCII control characters (0x00-0x1F, 0x7F)
    for ch in stripped:
        code_point = ord(ch)
        if code_point < 32 or code_point == 127:
            return False, "", "", "URL contains illegal control characters or null bytes."

    # Reject CRLF injection patterns
    if CRLF_REGEX.search(stripped):
        return False, "", "", "CRLF injection sequence detected."

    # Reject Unicode Format (Cf) or Control (Cc) characters
    for ch in stripped:
        cat = unicodedata.category(ch)
        if cat in ("Cf", "Cc"):
            return False, "", "", "URL contains illegal zero-width or format Unicode characters."

    # Reject internal whitespace
    if re.search(r"[\s\t\r\n]", stripped):
        return False, "", "", "URL contains internal whitespace or tab characters."

    # Enforce strict http/https scheme check
    if not re.match(r"^https?://", stripped, re.IGNORECASE):
        return False, "", "", "Unsupported URL scheme. Only HTTP and HTTPS are permitted."

    parsed = urllib.parse.urlsplit(stripped)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, "", "", f"Scheme '{scheme}' is prohibited."

    if not parsed.netloc:
        return False, "", "", "URL netloc/authority cannot be empty."

    # Reject embedded user credentials (user:pass@host)
    if "@" in parsed.netloc:
        return False, "", "", "Credential-stuffed authority (@) is prohibited."

    hostname = parsed.hostname
    if not hostname:
        return False, "", "", "URL hostname cannot be empty."

    # Convert hostname via IDNA (Punycode check)
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    except Exception:
        return False, "", "", "IDNA punycode encoding failed for hostname."

    if len(ascii_hostname) > 253:
        return False, "", "", "Hostname exceeds 253 characters."

    # SSRF & Self-Referential loop check
    if not allow_localhost:
        if ascii_hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"}:
            return False, "", "", "SSRF / Loopback target prohibited."

        if is_private_or_restricted_ip(ascii_hostname):
            return False, "", "", "Private network or cloud metadata IP prohibited."

        # Domain structure check: require at least one dot with >= 2-char TLD
        if "." not in ascii_hostname:
            return False, "", "", "Hostname must contain a valid top-level domain."

        tld = ascii_hostname.split(".")[-1]
        if len(tld) < 2 or tld.isdigit():
            # If not an allowed IP, must have a valid non-numeric TLD
            try:
                ipaddress.ip_address(ascii_hostname)
            except ValueError:
                return False, "", "", "Invalid domain structure or numeric TLD."

    # Canonicalize URL for SHA-256 hash
    port_part = ""
    if parsed.port:
        if (scheme == "http" and parsed.port != 80) or (scheme == "https" and parsed.port != 443):
            port_part = f":{parsed.port}"

    canonical_netloc = f"{ascii_hostname}{port_part}"
    path = parsed.path if parsed.path else "/"
    query = f"?{parsed.query}" if parsed.query else ""
    canonical_url = f"{scheme}://{canonical_netloc}{path}{query}"

    canonical_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
    return True, stripped, canonical_hash, ""


def validate_custom_alias(alias: Optional[str]) -> Tuple[bool, str]:
    """Validates custom alias format and reserved path denylist."""
    if not alias:
        return True, ""

    stripped = alias.strip()
    if not ALIAS_REGEX.match(stripped):
        return False, "Custom alias must be 3-32 alphanumeric characters, dashes, or underscores."

    if stripped.lower() in RESERVED_ROUTES:
        return False, f"Alias '{stripped}' collides with a reserved system endpoint."

    return True, ""


# ---------------------------------------------------------------------------
# Base62 Generation (M1)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Core URL Shortener Operations (M1 to M5)
# ---------------------------------------------------------------------------
def shorten_url(
    url: str,
    custom_alias: Optional[str] = None,
    expires_at: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
    db_path: Optional[Path] = None,
    allow_localhost: bool = False,
) -> Tuple[int, Dict[str, Any], bool]:
    """
    Shortens a URL, handling idempotency, custom aliases, and expiration.
    Returns: (status_code, response_data, escalated)
    """
    target_path = db_path if db_path is not None else DB_PATH
    init_db(target_path)
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()

    # URL validation
    is_valid, normalized_url, canonical_hash, err_msg = validate_and_normalize_url(
        url, allow_localhost=allow_localhost
    )
    if not is_valid:
        return 400, {"error": err_msg, "status": "REJECTED_MALICIOUS_OR_MALFORMED"}, True

    # Custom alias validation
    if custom_alias:
        alias_ok, alias_err = validate_custom_alias(custom_alias)
        if not alias_ok:
            return 400, {"error": alias_err, "status": "REJECTED_INVALID_ALIAS"}, True

    # Expiration parsing
    final_expires_at: Optional[str] = None
    if ttl_seconds is not None:
        if ttl_seconds < 0:
            return 400, {"error": "ttl_seconds cannot be negative", "status": "REJECTED"}, True
        if ttl_seconds == 0:
            # Immediate expiry: set 1 microsecond in the past to guarantee >= check passes
            expiry_dt = now - datetime.timedelta(microseconds=1)
        else:
            expiry_dt = now + datetime.timedelta(seconds=ttl_seconds)
        final_expires_at = expiry_dt.isoformat()
    elif expires_at:
        try:
            # Parse ISO-8601
            dt = datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            final_expires_at = dt.astimezone(datetime.timezone.utc).isoformat()
        except Exception:
            return 400, {"error": "Invalid expires_at format. Must be ISO-8601.", "status": "REJECTED"}, True

    with sqlite3.connect(target_path, timeout=5.0) as conn:
        cursor = conn.cursor()

        # Custom alias flow
        if custom_alias:
            cursor.execute("SELECT code FROM urls WHERE code = ?;", (custom_alias,))
            if cursor.fetchone():
                return 409, {"error": f"Alias '{custom_alias}' already exists.", "status": "CONFLICT_ALIAS"}, True

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
                "short_url": f"http://localhost:8000/{custom_alias}",
                "url": normalized_url,
                "original_url": normalized_url,
                "created_at": now_iso,
                "expires_at": final_expires_at,
                "escalated": False,
            }, False

        # Idempotency check (M4)
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
                # Check if existing link is expired
                is_expired = False
                if exp_at:
                    exp_dt = datetime.datetime.fromisoformat(exp_at)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
                    if now >= exp_dt:
                        is_expired = True

                if not is_expired:
                    # Idempotent hit (200 OK)
                    return 200, {
                        "code": existing_code,
                        "short_code": existing_code,
                        "short_url": f"http://localhost:8000/{existing_code}",
                        "url": orig_url,
                        "original_url": orig_url,
                        "created_at": c_at,
                        "expires_at": exp_at,
                        "escalated": bool(esc),
                    }, False

        # Mint new code (M1)
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
            "short_url": f"http://localhost:8000/{candidate_code}",
            "url": normalized_url,
            "original_url": normalized_url,
            "created_at": now_iso,
            "expires_at": final_expires_at,
            "escalated": False,
        }, False


def resolve_short_code(code: str, db_path: Optional[Path] = None) -> Tuple[int, Dict[str, Any], Optional[str]]:
    """
    Resolves short code: checks expiration (410), increments clicks, returns 302 with Location header.
    Returns: (status_code, data_or_error, redirect_url)
    """
    target_path = db_path if db_path is not None else DB_PATH
    init_db(target_path)
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    today_date = now.strftime("%Y-%m-%d")

    with sqlite3.connect(target_path, timeout=5.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT original_url, expires_at, total_clicks, escalated FROM urls WHERE code = ?;",
            (code,),
        )
        row = cursor.fetchone()
        if not row:
            return 404, {"detail": "Short code not found", "status": "UNKNOWN_CODE"}, None

        original_url, expires_at, total_clicks, escalated = row

        # Check expiration
        if expires_at:
            exp_dt = datetime.datetime.fromisoformat(expires_at)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
            if now >= exp_dt:
                return 410, {"detail": "Short link has expired", "status": "EXPIRED_GONE"}, None

        # Atomically increment total_clicks and last_accessed_at
        cursor.execute(
            """
            UPDATE urls
            SET total_clicks = total_clicks + 1, last_accessed_at = ?
            WHERE code = ?;
            """,
            (now_iso, code),
        )

        # Upsert daily clicks
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


def get_url_stats(code: str, db_path: Optional[Path] = None) -> Tuple[int, Dict[str, Any]]:
    """
    Retrieves full analytics payload for a given short code (M5).
    """
    target_path = db_path if db_path is not None else DB_PATH
    init_db(target_path)
    now = datetime.datetime.now(datetime.timezone.utc)

    with sqlite3.connect(target_path, timeout=5.0) as conn:
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

        # Daily clicks map
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


def get_health_status(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Returns database connectivity and operational metrics."""
    target_path = db_path if db_path is not None else DB_PATH
    init_db(target_path)
    chain_valid = verify_audit_chain(target_path)
    with sqlite3.connect(target_path, timeout=5.0) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM urls;")
        total_links = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(total_clicks), 0) FROM urls;")
        total_clicks = cursor.fetchone()[0]

    return {
        "status": "healthy",
        "database": "connected",
        "total_links": total_links,
        "total_clicks": total_clicks,
        "chain_valid": chain_valid,
    }


# ---------------------------------------------------------------------------
# Pre-Flight Input Normalization Wrapper & Core Agent Runner
# ---------------------------------------------------------------------------
def preflight_validate(raw_task: Any) -> Tuple[bool, str, List[str]]:
    """Defensively handles None, wrong types, empty inputs, or oversized payloads."""
    plan: List[str] = []

    if raw_task is None:
        plan.append("Preflight: Rejected null input (task is None).")
        return False, "", plan

    if not isinstance(raw_task, str):
        plan.append(f"Preflight: Type violation (expected str, got {type(raw_task).__name__}).")
        return False, str(raw_task), plan

    cleaned = raw_task.strip()
    if not cleaned:
        plan.append("Preflight: Rejected empty or whitespace-only task.")
        return False, "", plan

    if len(cleaned) > 10000:
        plan.append(f"Preflight: Task exceeded max length limit ({len(cleaned)} > 10000 chars).")
        return False, cleaned[:1000], plan

    plan.append("Preflight: Input validated successfully.")
    return True, cleaned, plan


def run(task: str) -> AgentResponse:
    """
    Main entry point evaluated by the automated grading harness.
    Returns: {"plan": list[str], "result": any, "escalated": bool}
    """
    plan: List[str] = []

    # Step 1: Preflight input check
    is_valid, normalized_task, preflight_plan = preflight_validate(task)
    plan.extend(preflight_plan)

    if not is_valid:
        log_audit_entry(
            task=str(task),
            confidence_score=0.0,
            risk_score=1.0,
            escalated=True,
            decision="PREFLIGHT_INPUT_REJECTION",
        )
        return {
            "plan": plan,
            "result": {"error": "Invalid input payload", "status": "REJECTED"},
            "escalated": True,
        }

    # Step 2: Layer 1 Security & Injection Canary
    is_suspicious, security_flags = detect_security_anomalies(normalized_task)
    if is_suspicious:
        for f in security_flags:
            plan.append(f"Security Alert: {f}")

        log_audit_entry(
            task=normalized_task,
            confidence_score=0.1,
            risk_score=1.0,
            escalated=True,
            decision="PROMPT_INJECTION_FLAGGED",
        )
        return {
            "plan": plan,
            "result": {
                "status": "SECURITY_BLOCK",
                "reason": "Hostile or injection patterns detected",
                "flags": security_flags,
            },
            "escalated": True,
        }

    # Step 3: Domain Logic Dispatch (JSON Payload or Natural Command)
    plan.append(f"Parsing shortener command: {normalized_task[:60]}...")
    payload: Dict[str, Any] = {}

    if normalized_task.startswith("{") and normalized_task.endswith("}"):
        try:
            payload = json.loads(normalized_task)
        except Exception:
            payload = {"action": "shorten", "url": normalized_task}
    else:
        # Check text command format
        parts = normalized_task.split(maxsplit=1)
        cmd = parts[0].lower()
        if cmd in ("shorten", "url") and len(parts) > 1:
            payload = {"action": "shorten", "url": parts[1].strip()}
        elif cmd in ("resolve", "get") and len(parts) > 1:
            payload = {"action": "resolve", "code": parts[1].strip()}
        elif cmd in ("stats", "analytics") and len(parts) > 1:
            payload = {"action": "stats", "code": parts[1].strip()}
        elif cmd == "health":
            payload = {"action": "health"}
        elif cmd == "audit":
            payload = {"action": "audit"}
        else:
            # Default to shorten if starts with http
            if normalized_task.startswith("http://") or normalized_task.startswith("https://"):
                payload = {"action": "shorten", "url": normalized_task}
            else:
                payload = {"action": "shorten", "url": normalized_task}

    action = payload.get("action", "shorten")

    if action == "shorten":
        target_url = payload.get("url") or payload.get("original_url") or payload.get("long_url", "")
        alias = payload.get("custom_alias") or payload.get("alias") or payload.get("custom_code")
        exp = payload.get("expires_at") or payload.get("expiry")
        # Use explicit None checks for ttl to correctly handle ttl_seconds=0
        ttl = payload.get("ttl_seconds")
        if ttl is None:
            ttl = payload.get("ttl")
        if ttl is None:
            ttl = payload.get("expires_in")
        allow_local = bool(payload.get("allow_localhost", False))

        plan.append(f"Action: shorten URL '{str(target_url)[:50]}'")
        status_code, result_data, escalated = shorten_url(
            url=str(target_url),
            custom_alias=str(alias) if alias else None,
            expires_at=str(exp) if exp else None,
            ttl_seconds=int(ttl) if ttl is not None else None,
            allow_localhost=allow_local,
        )

        decision = "SHORTEN_SUCCESS" if status_code in (200, 201) else "SHORTEN_REJECTED"
        confidence = 0.98 if status_code in (200, 201) else 0.20
        risk = 0.10 if status_code in (200, 201) else 0.90

        rec_hash = log_audit_entry(
            task=normalized_task,
            confidence_score=confidence,
            risk_score=risk,
            escalated=escalated,
            decision=decision,
        )
        plan.append(f"Result: HTTP {status_code} | Hash Chain: {rec_hash[:12]}...")

        return {
            "plan": plan,
            "result": {"status_code": status_code, "data": result_data},
            "escalated": escalated,
        }

    elif action == "resolve":
        code = payload.get("code", "")
        plan.append(f"Action: resolve short code '{code}'")
        status_code, result_data, redirect_url = resolve_short_code(code)

        rec_hash = log_audit_entry(
            task=normalized_task,
            confidence_score=0.95 if status_code == 302 else 0.50,
            risk_score=0.10 if status_code == 302 else 0.60,
            escalated=(status_code == 410 or status_code == 404),
            decision=f"RESOLVE_{status_code}",
        )
        plan.append(f"Result: HTTP {status_code} | Hash Chain: {rec_hash[:12]}...")

        return {
            "plan": plan,
            "result": {
                "status_code": status_code,
                "data": result_data,
                "location": redirect_url,
            },
            "escalated": False,
        }

    elif action == "stats":
        code = payload.get("code", "")
        plan.append(f"Action: get analytics for '{code}'")
        status_code, result_data = get_url_stats(code)

        rec_hash = log_audit_entry(
            task=normalized_task,
            confidence_score=0.95 if status_code == 200 else 0.50,
            risk_score=0.10,
            escalated=False,
            decision=f"STATS_{status_code}",
        )
        plan.append(f"Result: HTTP {status_code} | Hash Chain: {rec_hash[:12]}...")

        return {
            "plan": plan,
            "result": {"status_code": status_code, "data": result_data},
            "escalated": False,
        }

    elif action == "health":
        health_data = get_health_status()
        plan.append("Action: health check executed")
        return {
            "plan": plan,
            "result": health_data,
            "escalated": not health_data["chain_valid"],
        }

    elif action == "audit":
        audit_md = export_audit_markdown()
        plan.append("Action: exported audit markdown")
        return {
            "plan": plan,
            "result": {"audit_markdown": audit_md, "verified": verify_audit_chain()},
            "escalated": False,
        }

    else:
        plan.append(f"Unknown action: '{action}'")
        return {
            "plan": plan,
            "result": {"error": f"Unknown action: {action}"},
            "escalated": True,
        }


if __name__ == "__main__":
    test_run = run("https://example.com/test-sdsi-link")
    print(json.dumps(test_run, indent=2))
