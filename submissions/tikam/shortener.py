"""Core URL-shortener business logic.

Validation · normalisation · Base62 generation · resolve · stats.
No Streamlit dependency — this module is pure domain logic.
"""

from __future__ import annotations

import re
import string
import secrets
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urlunparse

from database import get_db, init_db

# ── constants ──────────────────────────────────────────────────────────
BASE62_ALPHABET = string.digits + string.ascii_uppercase + string.ascii_lowercase  # 62 chars
BASE = 62
CODE_LENGTH = 6          # default auto-generated length
MAX_CODE_LENGTH = 8      # fallback if 6-char space is exhausted
MAX_URL_LENGTH = 2048
MAX_ALIAS_LENGTH = 32
MIN_ALIAS_LENGTH = 4

BLOCKED_SCHEMES = frozenset({"javascript", "data", "file", "ftp", "vbscript", "about"})
ALLOWED_SCHEMES = frozenset({"http", "https"})

RESERVED_WORDS = frozenset({"stats", "api", "admin", "login", "shorten", "resolve", "health", "404", "410"})

ALIAS_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


# ── exceptions ─────────────────────────────────────────────────────────
class ShortenerError(ValueError):
    """User-facing error for invalid input."""


# ── helpers ────────────────────────────────────────────────────────────
def _encode_base62(num: int) -> str:
    """Convert an integer to a Base62 string."""
    if num == 0:
        return BASE62_ALPHABET[0]
    chars: list[str] = []
    while num > 0:
        num, rem = divmod(num, BASE)
        chars.append(BASE62_ALPHABET[rem])
    return "".join(reversed(chars))


def _random_code(length: int = CODE_LENGTH) -> str:
    """Generate a cryptographically-random Base62 string."""
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))


# ── validation ─────────────────────────────────────────────────────────
def validate_url(raw: str) -> str:
    """Validate *raw* and return a canonical normalised form.

    Raises ``ShortenerError`` for anything unsafe or malformed.
    """
    if not raw or not raw.strip():
        raise ShortenerError("URL cannot be empty.")

    url = raw.strip()

    if len(url) > MAX_URL_LENGTH:
        raise ShortenerError(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters.")

    # Block dangerous schemes early (case-insensitive)
    url_lower = url.lower()
    for scheme in BLOCKED_SCHEMES:
        if url_lower.startswith(f"{scheme}:"):
            raise ShortenerError(f"Scheme '{scheme}:' is blocked for security reasons.")

    try:
        parsed = urlparse(url)
    except Exception:
        raise ShortenerError("Malformed URL — could not parse.")

    if not parsed.scheme:
        raise ShortenerError("URL must include a scheme (http:// or https://).")

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ShortenerError(f"Only http / https URLs are allowed, got '{parsed.scheme}'.")

    if not parsed.netloc:
        raise ShortenerError("URL must include a valid hostname.")

    # Reject loopback / internal addresses
    host = parsed.netloc.lower().split(":")[0]
    # IPv6 loopbacks like ::1 get mangled by split — check netloc directly
    bare_netloc = parsed.netloc.lower()
    if host in {"localhost", "127.0.0.1", "0.0.0.0"} or bare_netloc in {"::1", "[::1]"}:
        raise ShortenerError("Localhost URLs are not allowed.")

    # Normalise
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"

    # Strip trailing slash except for bare "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    # Remove default ports
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    return urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))


def validate_alias(alias: str) -> str:
    """Validate and return a cleaned custom alias.

    Raises ``ShortenerError`` on invalid input.
    """
    if not alias or not alias.strip():
        raise ShortenerError("Custom alias cannot be empty.")

    alias = alias.strip()

    if len(alias) < MIN_ALIAS_LENGTH:
        raise ShortenerError(f"Custom alias must be at least {MIN_ALIAS_LENGTH} characters.")
    if len(alias) > MAX_ALIAS_LENGTH:
        raise ShortenerError(f"Custom alias must be at most {MAX_ALIAS_LENGTH} characters.")

    if not ALIAS_RE.match(alias):
        raise ShortenerError("Custom alias can only contain a-z, A-Z, 0-9, hyphen, and underscore.")

    if alias.lower() in RESERVED_WORDS:
        raise ShortenerError(f"'{alias}' is a reserved word and cannot be used.")

    return alias


# ── core operations ────────────────────────────────────────────────────
def shorten(url: str, custom_alias: str | None = None, expiry_hours: int | None = None) -> dict:
    """Shorten a URL.  Same URL + no custom alias → same short code (idempotent).

    Returns a dict with keys:
        short_code, original_url, normalized_url, is_existing, expires_at
    """
    normalized = validate_url(url)

    if custom_alias:
        custom_alias = validate_alias(custom_alias)

    if expiry_hours is not None:
        if not isinstance(expiry_hours, int) or expiry_hours <= 0:
            raise ShortenerError("Expiry hours must be a positive integer.")
        if expiry_hours > 8760:  # 1 year
            raise ShortenerError("Expiry cannot exceed 1 year (8760 hours).")

    db = get_db()

    # ── idempotency: same normalised URL → same code (non-custom only) ──
    if not custom_alias:
        row = db.execute(
            """SELECT short_code, is_custom
               FROM urls
               WHERE normalized_url = ?
                 AND (expires_at IS NULL OR expires_at > datetime('now'))
               ORDER BY created_at DESC
               LIMIT 1""",
            (normalized,),
        ).fetchone()
        if row:
            db.close()
            return {
                "short_code": row["short_code"],
                "original_url": url,
                "normalized_url": normalized,
                "is_existing": True,
                "expires_at": None,
            }

    # ── custom alias collision check ──
    if custom_alias:
        if db.execute("SELECT 1 FROM urls WHERE short_code = ?", (custom_alias,)).fetchone():
            db.close()
            raise ShortenerError(f"Custom alias '{custom_alias}' is already taken.")
        short_code = custom_alias
    else:
        short_code = _generate_unique_code(db)

    # ── insert ──
    now = datetime.now(timezone.utc)
    expires_at_str: str | None = None
    if expiry_hours:
        expires_dt = now + timedelta(hours=expiry_hours)
        expires_at_str = expires_dt.strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        """INSERT INTO urls (short_code, original_url, normalized_url, is_custom, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (short_code, url, normalized, int(bool(custom_alias)), now.strftime("%Y-%m-%d %H:%M:%S"), expires_at_str),
    )
    db.commit()
    db.close()

    return {
        "short_code": short_code,
        "original_url": url,
        "normalized_url": normalized,
        "is_existing": False,
        "expires_at": expires_at_str,
    }


def _generate_unique_code(db) -> str:
    """Try 6-char codes first; fall back to 7 then 8 chars."""
    for length in range(CODE_LENGTH, MAX_CODE_LENGTH + 1):
        for _ in range(20):  # attempts per length
            code = _random_code(length)
            if not db.execute("SELECT 1 FROM urls WHERE short_code = ?", (code,)).fetchone():
                return code
    raise ShortenerError("Could not generate a unique short code. Please try again.")


def resolve(short_code: str) -> dict:
    """Look up a short code.

    Returns dict with keys:
        status     — "found" | "expired" | "not_found"
        url        — original URL (only when found)
        expires_at — (only when expired)
    Also records a click when found (but not redirecting to expired).
    """
    if not short_code or not short_code.strip():
        return {"status": "not_found"}

    code = short_code.strip()

    db = get_db()
    row = db.execute(
        "SELECT original_url, expires_at FROM urls WHERE short_code = ?",
        (code,),
    ).fetchone()

    if row is None:
        db.close()
        return {"status": "not_found"}

    # Check expiry
    if row["expires_at"] is not None:
        expires_dt = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expires_dt:
            db.close()
            return {"status": "expired", "expires_at": row["expires_at"]}

    # Record click
    db.execute("INSERT INTO clicks (short_code) VALUES (?)", (code,))
    db.commit()
    url = row["original_url"]
    db.close()

    return {"status": "found", "url": url}


def get_stats(short_code: str) -> dict | None:
    """Return aggregate stats for *short_code*, or None if the code doesn't exist."""
    if not short_code or not short_code.strip():
        return None

    code = short_code.strip()

    db = get_db()

    url_row = db.execute(
        "SELECT original_url, normalized_url, created_at, expires_at FROM urls WHERE short_code = ?",
        (code,),
    ).fetchone()

    if url_row is None:
        db.close()
        return None

    total_clicks = db.execute(
        "SELECT COUNT(*) AS cnt FROM clicks WHERE short_code = ?", (code,)
    ).fetchone()["cnt"]

    per_day_rows = db.execute(
        """SELECT DATE(clicked_at) AS day, COUNT(*) AS cnt
           FROM clicks WHERE short_code = ?
           GROUP BY day ORDER BY day""",
        (code,),
    ).fetchall()

    last_accessed_row = db.execute(
        "SELECT MAX(clicked_at) AS last FROM clicks WHERE short_code = ?", (code,)
    ).fetchone()

    db.close()

    return {
        "short_code": code,
        "original_url": url_row["original_url"],
        "normalized_url": url_row["normalized_url"],
        "created_at": url_row["created_at"],
        "expires_at": url_row["expires_at"],
        "total_clicks": total_clicks,
        "clicks_per_day": {r["day"]: r["cnt"] for r in per_day_rows},
        "last_accessed": last_accessed_row["last"],
    }


def list_all_urls() -> list[dict]:
    """Return every shortened URL (for the admin / stats dashboard)."""
    db = get_db()
    rows = db.execute(
        """SELECT u.short_code, u.original_url, u.normalized_url, u.is_custom,
                  u.created_at, u.expires_at,
                  (SELECT COUNT(*) FROM clicks c WHERE c.short_code = u.short_code) AS clicks
           FROM urls u
           ORDER BY u.created_at DESC
           LIMIT 200"""
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]