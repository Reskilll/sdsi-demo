"""
Security & Blast-Radius Mitigation Engine
Enforces M3 URL validation, SSRF/XSS defense, anti-smuggling, and rate limiting.
"""

from __future__ import annotations

import collections
import hashlib
import ipaddress
import os
import re
import time
import unicodedata
import urllib.parse
from typing import Optional, Tuple

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

CRLF_REGEX = re.compile(r"[\r\n]|(%0[adAD])")
ALIAS_REGEX = re.compile(r"^[0-9A-Za-z_-]{3,32}$")


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter for bot velocity and click-flood protection."""

    def __init__(self, max_requests: int = 100, window_seconds: float = 5.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.events: collections.defaultdict[str, collections.deque[float]] = collections.defaultdict(
            collections.deque
        )

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        q = self.events[key]
        while q and q[0] <= now - self.window_seconds:
            q.popleft()
        if len(q) >= self.max_requests:
            return True
        q.append(now)
        return False


# Global rate limiters
resolution_rate_limiter = SlidingWindowRateLimiter(max_requests=100, window_seconds=5.0)
shorten_rate_limiter = SlidingWindowRateLimiter(max_requests=30, window_seconds=60.0)


def is_private_or_restricted_ip(ip_str: str) -> bool:
    """Identifies loopback, private RFC 1918, link-local metadata, or broadcast IPs."""
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


def validate_url(raw_url: str) -> Tuple[bool, str, str, str]:
    """
    Validates URL according to M3 standard and blast-radius constraints.
    Returns: (is_valid, normalized_url, canonical_hash, error_reason)
    """
    allow_localhost = os.getenv("ALLOW_LOCALHOST", "0") == "1"

    if not isinstance(raw_url, str):
        return False, "", "", "URL must be a string."

    stripped = raw_url.strip()
    if not stripped:
        return False, "", "", "URL cannot be empty."

    if len(stripped) > 2048:
        return False, "", "", "URL exceeds maximum permitted length of 2048 characters."

    # Reject null bytes and raw ASCII control characters
    for ch in stripped:
        cp = ord(ch)
        if cp < 32 or cp == 127:
            return False, "", "", "Illegal ASCII control characters or null bytes detected in URL."

    # Reject CRLF injection sequences
    if CRLF_REGEX.search(stripped):
        return False, "", "", "CRLF response-splitting injection pattern detected."

    # Reject Unicode Format (Cf) or Control (Cc) characters (zero-width smuggling)
    for ch in stripped:
        cat = unicodedata.category(ch)
        if cat in ("Cf", "Cc"):
            return False, "", "", "Illegal zero-width or formatting Unicode characters detected in URL."

    # Reject internal whitespace/tabs
    if re.search(r"[\s\t\r\n]", stripped):
        return False, "", "", "Internal whitespace or tab characters detected in URL."

    # Enforce strict http/https scheme on raw input
    if not re.match(r"^https?://", stripped, re.IGNORECASE):
        return False, "", "", "Unsupported URL scheme. Only HTTP and HTTPS are permitted."

    parsed = urllib.parse.urlsplit(stripped)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, "", "", f"Scheme '{scheme}' is prohibited."

    if not parsed.netloc:
        return False, "", "", "URL authority/netloc cannot be empty."

    # Prohibit credential stuffing (@)
    if "@" in parsed.netloc:
        return False, "", "", "Credential-stuffed authority (@) is prohibited."

    hostname = parsed.hostname
    if not hostname:
        return False, "", "", "URL hostname cannot be empty."

    # IDNA encoding check
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    except Exception:
        return False, "", "", "IDNA punycode normalization failed."

    if len(ascii_hostname) > 253:
        return False, "", "", "Hostname exceeds RFC limit of 253 characters."

    # SSRF / Self-Referential redirect prevention
    if not allow_localhost:
        if ascii_hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"}:
            return False, "", "", "SSRF / Loopback target is strictly prohibited."

        if is_private_or_restricted_ip(ascii_hostname):
            return False, "", "", "Private network or cloud metadata IP target is prohibited."

        if "." not in ascii_hostname:
            return False, "", "", "Hostname must have a valid top-level domain."

        tld = ascii_hostname.split(".")[-1]
        if len(tld) < 2 or tld.isdigit():
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
    """Validates custom alias format and reserved endpoints."""
    if not alias:
        return True, ""

    stripped = alias.strip()
    if not ALIAS_REGEX.match(stripped):
        return False, "Custom alias must be 3-32 alphanumeric characters, dashes, or underscores."

    if stripped.lower() in RESERVED_ROUTES:
        return False, f"Alias '{stripped}' collides with a reserved system route."

    return True, ""
