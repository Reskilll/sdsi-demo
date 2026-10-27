"""Tests for the URL shortener.

Run with:  python -m pytest submissions/tikam/test_shortener.py -v
"""

import pytest
import re
from datetime import datetime, timezone, timedelta

from shortener import (
    validate_url,
    validate_alias,
    shorten,
    resolve,
    get_stats,
    ShortenerError,
)
from database import init_db, get_db
from database import DB_PATH

# Ensure DB is initialised
init_db()


def _clean_db():
    """Wipe data between tests for isolation."""
    db = get_db()
    db.execute("DELETE FROM clicks")
    db.execute("DELETE FROM urls")
    db.commit()
    db.close()


# ── URL validation ─────────────────────────────────────────────────────
class TestValidateURL:
    def test_accepts_https(self):
        assert validate_url("https://example.com") == "https://example.com/"

    def test_accepts_http(self):
        assert validate_url("http://example.com/path") == "http://example.com/path"

    def test_normalises_scheme_lowercase(self):
        result = validate_url("HTTPS://EXAMPLE.COM/Path")
        assert result == "https://example.com/Path"

    def test_strips_trailing_slash(self):
        result = validate_url("https://example.com/page/")
        assert result == "https://example.com/page"

    def test_keeps_root_trailing_slash(self):
        result = validate_url("https://example.com/")
        assert result == "https://example.com/"

    def test_removes_default_http_port(self):
        result = validate_url("http://example.com:80/path")
        assert result == "http://example.com/path"

    def test_removes_default_https_port(self):
        result = validate_url("https://example.com:443/path")
        assert result == "https://example.com/path"

    @pytest.mark.parametrize("url", [
        "",
        "   ",
        "not-a-url",
        "ftp://example.com",
        "javascript:alert(1)",
        "javascript:void(0)",
        "JAVASCRIPT:alert('xss')",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "http://localhost/admin",
        "http://127.0.0.1",
        "http://::1",
        "http://0.0.0.0",
    ])
    def test_rejects_dangerous_input(self, url):
        with pytest.raises(ShortenerError):
            validate_url(url)

    def test_rejects_url_too_long(self):
        long_url = "https://example.com/" + "a" * 2100
        with pytest.raises(ShortenerError):
            validate_url(long_url)

    def test_rejects_no_scheme(self):
        with pytest.raises(ShortenerError):
            validate_url("example.com/page")

    def test_accepts_unicode_path(self):
        result = validate_url("https://example.com/路径?q=测试")
        # Python's urlparse preserves Unicode; the URL is valid as-is
        assert result == "https://example.com/路径?q=测试"


# ── alias validation ───────────────────────────────────────────────────
class TestValidateAlias:
    def test_accepts_valid_alias(self):
        assert validate_alias("my-link") == "my-link"

    def test_rejects_short_alias(self):
        with pytest.raises(ShortenerError):
            validate_alias("abc")

    def test_rejects_special_chars(self):
        with pytest.raises(ShortenerError):
            validate_alias("my link!")

    def test_rejects_reserved_word(self):
        with pytest.raises(ShortenerError):
            validate_alias("admin")

    def test_rejects_empty(self):
        with pytest.raises(ShortenerError):
            validate_alias("   ")

    def test_rejects_too_long(self):
        with pytest.raises(ShortenerError):
            validate_alias("a" * 33)


# ── shorten → resolve → stats lifecycle ────────────────────────────────
class TestShortenResolve:
    @pytest.fixture(autouse=True)
    def setup(self):
        _clean_db()

    def test_shorten_and_resolve(self):
        result = shorten("https://example.com/hello")
        assert len(result["short_code"]) == 6
        assert result["is_existing"] is False

        resolved = resolve(result["short_code"])
        assert resolved["status"] == "found"
        assert resolved["url"] == "https://example.com/hello"

    def test_same_url_returns_same_code(self):
        r1 = shorten("https://example.com/dup")
        r2 = shorten("https://example.com/dup")
        assert r1["short_code"] == r2["short_code"]
        assert r2["is_existing"] is True

    def test_same_url_different_trailing_slash_idempotent(self):
        r1 = shorten("https://example.com/dup2/")
        r2 = shorten("https://example.com/dup2")
        assert r1["short_code"] == r2["short_code"]

    def test_different_urls_different_codes(self):
        r1 = shorten("https://example.com/a")
        r2 = shorten("https://example.com/b")
        assert r1["short_code"] != r2["short_code"]

    def test_custom_alias(self):
        result = shorten("https://example.com/custom", custom_alias="my-ref")
        assert result["short_code"] == "my-ref"

    def test_custom_alias_collision(self):
        shorten("https://example.com/one", custom_alias="unique1")
        with pytest.raises(ShortenerError, match="already taken"):
            shorten("https://example.com/two", custom_alias="unique1")

    def test_resolve_unknown_code(self):
        assert resolve("ZZZZZZ")["status"] == "not_found"

    def test_expired_link(self):
        from database import get_db

        db = get_db()
        db.execute(
            "INSERT INTO urls (short_code, original_url, normalized_url, expires_at) VALUES (?, ?, ?, ?)",
            ("exp123", "https://example.com/old", "https://example.com/old",
             "2020-01-01 00:00:00"),
        )
        db.commit()
        db.close()

        resolved = resolve("exp123")
        assert resolved["status"] == "expired"

    def test_clicks_recorded(self):
        result = shorten("https://example.com/clicks")
        code = result["short_code"]
        resolve(code)  # click 1
        resolve(code)  # click 2

        stats = get_stats(code)
        assert stats["total_clicks"] == 2

    def test_stats_unknown_code(self):
        assert get_stats("NONEXIST") is None

    def test_empty_resolve(self):
        assert resolve("")["status"] == "not_found"
        assert resolve("   ")["status"] == "not_found"

    def test_expiry_rejects_negative(self):
        with pytest.raises(ShortenerError):
            shorten("https://example.com/exp", expiry_hours=-1)

    def test_expiry_rejects_zero(self):
        with pytest.raises(ShortenerError):
            shorten("https://example.com/exp", expiry_hours=0)

    def test_short_code_is_base62(self):
        result = shorten("https://example.com/base62-test")
        assert re.fullmatch(r"[a-zA-Z0-9]{6,8}", result["short_code"]) is not None


# ── run with pytest ────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v"])