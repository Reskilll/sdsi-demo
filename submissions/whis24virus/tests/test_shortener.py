"""
Comprehensive Pytest Test Suite for PS3 High-Assurance URL Shortener
Covers M1-M5, Adversarial Red-Teaming, SSRF/XSS Attacks, Expiration, Idempotency, and Concurrency.
"""

import concurrent.futures
import os
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.service import verify_security_chain
from app.database import get_connection


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Configures an isolated SQLite database for each test session."""
    test_db = tmp_path / "test_shortener.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(test_db))
    monkeypatch.setenv("ALLOW_LOCALHOST", "0")
    init_db(test_db)
    yield test_db


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ===========================================================================
# M1: Encoding & Custom Alias Tests
# ===========================================================================
def test_m1_standard_shortening(client):
    """M1: Valid URL mints a 6-8 character Base62 code."""
    res = client.post("/shorten", json={"url": "https://example.com/docs/api"})
    assert res.status_code == 201
    data = res.json()
    assert "code" in data
    assert 6 <= len(data["code"]) <= 8
    assert data["code"].isalnum()
    assert data["url"] == "https://example.com/docs/api"
    assert data["escalated"] is False


def test_m1_custom_alias_valid(client):
    """M1: User can supply a custom alphanumeric alias."""
    res = client.post("/shorten", json={"url": "https://example.com/target", "custom_alias": "custom-link_01"})
    assert res.status_code == 201
    assert res.json()["code"] == "custom-link_01"


def test_m1_custom_alias_duplicate_conflict(client):
    """M1: Reusing an existing custom alias triggers HTTP 409 Conflict."""
    client.post("/shorten", json={"url": "https://example.com/1", "custom_alias": "dup_alias"})
    res2 = client.post("/shorten", json={"url": "https://example.com/2", "custom_alias": "dup_alias"})
    assert res2.status_code == 409


@pytest.mark.parametrize("reserved", ["api", "shorten", "urls", "stats", "health", "metrics", "docs", "redoc", "openapi.json"])
def test_m1_reserved_alias_rejected(client, reserved):
    """M1: System-reserved endpoint names cannot be hijacked as aliases."""
    res = client.post("/shorten", json={"url": "https://example.com/evil", "custom_alias": reserved})
    assert res.status_code in (400, 409)


# ===========================================================================
# M2: Resolution & Lifecycle Tests
# ===========================================================================
def test_m2_redirect_302(client):
    """M2: Valid code returns 302 with exact Location header and no-cache header."""
    create_res = client.post("/shorten", json={"url": "https://example.com/redirect-target"})
    code = create_res.json()["code"]

    res = client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["Location"] == "https://example.com/redirect-target"
    assert "no-store" in res.headers["Cache-Control"]


def test_m2_unknown_code_404(client):
    """M2: Non-existent code returns HTTP 404 Not Found."""
    res = client.get("/nonEx1st", follow_redirects=False)
    assert res.status_code == 404


def test_m2_expired_code_410(client):
    """M2: Expired link returns HTTP 410 Gone and does NOT count clicks."""
    # Create with 1 second TTL
    create_res = client.post(
        "/shorten",
        json={"url": "https://example.com/expires-fast", "ttl_seconds": 0},
    )
    code = create_res.json()["code"]

    # Sleep briefly to ensure expiration
    time.sleep(0.05)
    res = client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 410

    # Verify stats click count is still 0
    stats = client.get(f"/stats/{code}").json()
    assert stats["total_clicks"] == 0
    assert stats["is_expired"] is True


# ===========================================================================
# M3: Adversarial Validation & Security Gate Tests
# ===========================================================================
@pytest.mark.parametrize(
    "malicious_url",
    [
        "javascript:alert(1)",
        "JAVASCRIPT:alert(document.domain)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "file:///C:/Windows/win.ini",
        "ftp://anonymous@ftp.example.com/file",
        "ws://example.com/socket",
        "mailto:victim@example.com",
    ],
)
def test_m3_rejects_dangerous_schemes(client, malicious_url):
    """M3: Rejects dangerous non-HTTP/HTTPS schemes with HTTP 400."""
    res = client.post("/shorten", json={"url": malicious_url})
    assert res.status_code == 400


@pytest.mark.parametrize(
    "ssrf_target",
    [
        "http://localhost/admin",
        "http://127.0.0.1/etc",
        "http://0.0.0.0:8080/metrics",
        "http://[::1]/secret",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "http://172.16.0.1/cloud",
    ],
)
def test_m3_rejects_ssrf_targets(client, ssrf_target):
    """M3: Rejects private network and loopback SSRF targets with HTTP 400."""
    res = client.post("/shorten", json={"url": ssrf_target})
    assert res.status_code == 400


def test_m3_rejects_credential_stuffing(client):
    """M3: Rejects embedded user:password credentials in authority."""
    res = client.post("/shorten", json={"url": "https://admin:pass123@example.com/login"})
    assert res.status_code == 400


def test_m3_rejects_crlf_injection(client):
    """M3: Rejects CRLF HTTP response splitting payload."""
    res = client.post("/shorten", json={"url": "https://example.com/path%0d%0aSet-Cookie:admin=1"})
    assert res.status_code == 400


def test_m3_rejects_zero_width_unicode(client):
    """M3: Rejects invisible zero-width unicode characters in URL."""
    res = client.post("/shorten", json={"url": "https://ex\u200bample.com/test"})
    assert res.status_code == 400


def test_m3_rejects_missing_scheme_and_empty_host(client):
    """M3: Rejects missing scheme and empty hostname."""
    assert client.post("/shorten", json={"url": "www.google.com"}).status_code == 400
    assert client.post("/shorten", json={"url": "https://"}).status_code == 400
    assert client.post("/shorten", json={"url": "https:///path"}).status_code == 400


def test_m3_rejects_oversized_url(client):
    """M3: Rejects URLs exceeding 2048 characters."""
    long_url = "https://example.com/" + "a" * 2100
    res = client.post("/shorten", json={"url": long_url})
    assert res.status_code == 400


# ===========================================================================
# M4: Canonicalization & Idempotency Tests
# ===========================================================================
def test_m4_idempotent_duplicate_submission(client):
    """M4: Submitting identical URL twice returns the same short code."""
    res1 = client.post("/shorten", json={"url": "https://example.com/idempotent-page"})
    assert res1.status_code == 201
    code1 = res1.json()["code"]

    res2 = client.post("/shorten", json={"url": "https://example.com/idempotent-page"})
    assert res2.status_code in (200, 201)
    code2 = res2.json()["code"]

    assert code1 == code2


def test_m4_idempotent_normalization(client):
    """M4: Normalized variants (default ports, hostname casing) produce identical short code."""
    res1 = client.post("/shorten", json={"url": "https://EXAMPLE.COM:443/docs?q=1"})
    res2 = client.post("/shorten", json={"url": "https://example.com/docs?q=1"})

    assert res1.json()["code"] == res2.json()["code"]


def test_m4_custom_alias_separate_from_canonical(client):
    """M4: Submitting the same URL with a custom alias produces a distinct entry."""
    res1 = client.post("/shorten", json={"url": "https://example.com/shared"})
    res2 = client.post("/shorten", json={"url": "https://example.com/shared", "custom_alias": "custom-shared"})

    assert res1.json()["code"] != res2.json()["code"]
    assert res2.json()["code"] == "custom-shared"


def test_m4_expired_url_remints_fresh_code(client):
    """M4: Shortening a URL whose prior link expired mints an active new code."""
    res1 = client.post("/shorten", json={"url": "https://example.com/exp-remint", "ttl_seconds": 0})
    time.sleep(0.05)

    res2 = client.post("/shorten", json={"url": "https://example.com/exp-remint"})
    assert res2.status_code == 201
    assert res2.json()["expires_at"] is None


# ===========================================================================
# M5: Telemetry & Analytics Tests
# ===========================================================================
def test_m5_analytics_counters(client):
    """M5: Click counter starts at 0, increments on redirect, and updates daily buckets."""
    create_res = client.post("/shorten", json={"url": "https://example.com/telemetry"})
    code = create_res.json()["code"]

    # Initial stats
    stats1 = client.get(f"/stats/{code}").json()
    assert stats1["total_clicks"] == 0

    # Fire 3 redirects
    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False)

    stats2 = client.get(f"/stats/{code}").json()
    assert stats2["total_clicks"] == 3
    assert stats2["clicks"] == 3
    assert len(stats2["clicks_per_day"]) >= 1
    assert stats2["last_accessed_at"] is not None


def test_m5_stats_unknown_code_404(client):
    """M5: Querying stats for missing code returns 404."""
    res = client.get("/stats/nonExistent99")
    assert res.status_code == 404


# ===========================================================================
# Bonus: Health & Cryptographic Audit Chain Tests
# ===========================================================================
def test_health_endpoint(client):
    """Health check confirms DB connectivity and audit chain status."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["chain_valid"] is True


def test_security_audit_chain(client):
    """Blocked malicious requests trigger tamper-evident audit chain logging."""
    client.post("/shorten", json={"url": "javascript:alert(1)"})
    audit_res = client.get("/api/audit")
    assert audit_res.status_code == 200
    records = audit_res.json()["audit_records"]
    assert len(records) >= 1
    assert records[0]["escalated"] is True

    # Cryptographic integrity check
    with get_connection() as conn:
        assert verify_security_chain(conn) is True


# ===========================================================================
# Concurrency & High-Throughput Verification
# ===========================================================================
def test_concurrent_idempotency_and_clicks(client):
    """Concurrent requests execute cleanly with WAL mode and zero DB lock errors."""
    target_url = "https://example.com/concurrent-test"

    # 10 parallel requests shortening the same URL
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(client.post, "/shorten", json={"url": target_url}) for _ in range(10)]
        codes = [f.result().json()["code"] for f in futures]

    # All parallel calls received the exact same code
    assert len(set(codes)) == 1
    common_code = codes[0]

    # 20 parallel click resolutions
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        click_futures = [executor.submit(client.get, f"/{common_code}", follow_redirects=False) for _ in range(20)]
        statuses = [f.result().status_code for f in click_futures]

    assert all(s == 302 for s in statuses)
    stats = client.get(f"/stats/{common_code}").json()
    assert stats["total_clicks"] == 20
