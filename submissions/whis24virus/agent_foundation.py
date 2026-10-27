"""
Agent Foundation & Security Architecture for SDSI Digithon
Author: whis24virus
Standard Library Only (Zero External Dependencies)
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

# Strict local path resolution (eliminates cwd path bugs)
DB_PATH = Path(__file__).resolve().parent / "audit.db"

# ---------------------------------------------------------------------------
# Strict Return Contract
# ---------------------------------------------------------------------------
class AgentResponse(TypedDict):
    plan: List[str]
    result: Any
    escalated: bool


# ---------------------------------------------------------------------------
# Layer 1: Prompt Injection & Adversarial Heuristics Gate
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


def detect_security_anomalies(text: str) -> Tuple[bool, List[str]]:
    """Scans untrusted input for prompt injection, zero-width chars, and escape vectors."""
    flags: List[str] = []

    # Check zero-width obfuscation
    if ZERO_WIDTH_CHARS.search(text):
        flags.append("Obfuscation: zero-width unicode characters detected")

    # Check pattern heuristics
    for pattern in INJECTION_SIGNATURES:
        if re.search(pattern, text):
            flags.append(f"Prompt Injection Pattern: {pattern}")

    return len(flags) > 0, flags


# ---------------------------------------------------------------------------
# Layer 2: Tamper-Evident SHA-256 Chained SQLite Audit Log
# ---------------------------------------------------------------------------
def init_db(db_path: Path = DB_PATH) -> None:
    """Initializes audit database with WAL mode and hash-chain schema."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
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
        conn.commit()


def log_audit_entry(
    task: str,
    confidence_score: float,
    risk_score: float,
    escalated: bool,
    decision: str,
    db_path: Path = DB_PATH,
) -> str:
    """Computes SHA-256 hash chain and appends a tamper-evident audit record."""
    init_db(db_path)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    task_hash = hashlib.sha256(task.encode("utf-8", errors="replace")).hexdigest()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Fetch latest record_hash to chain
        cursor.execute("SELECT record_hash FROM audit_logs ORDER BY id DESC LIMIT 1;")
        row = cursor.fetchone()
        prev_hash = row[0] if row else "GENESIS_ROOT_HASH_000000000000000000000000"

        # Compute tamper-evident record hash
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


def verify_audit_chain(db_path: Path = DB_PATH) -> bool:
    """Cryptographically verifies the integrity of the entire audit hash-chain."""
    if not db_path.exists():
        return True

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, task_hash, prev_hash, record_hash, confidence_score, risk_score, escalated, decision FROM audit_logs ORDER BY id ASC;"
        )
        rows = cursor.fetchall()

    expected_prev = "GENESIS_ROOT_HASH_000000000000000000000000"
    for r in rows:
        _id, ts, task_h, prev_h, rec_h, conf, risk, esc, dec = r
        if prev_h != expected_prev:
            return False  # Chain broken!

        expected_hash = hashlib.sha256(
            f"{prev_h}|{ts}|{task_h}|{conf:.2f}|{risk:.2f}|{esc}|{dec}".encode("utf-8")
        ).hexdigest()

        if rec_h != expected_hash:
            return False  # Record tampered!

        expected_prev = rec_h

    return True


def export_audit_markdown(limit: int = 5, db_path: Path = DB_PATH) -> str:
    """Exports the latest audit records formatted as a Markdown table (ideal for diff proof)."""
    if not db_path.exists():
        return "_No audit records logged._"

    with sqlite3.connect(db_path) as conn:
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
# Pre-Flight Input Normalization Wrapper & Core Runner
# ---------------------------------------------------------------------------
def preflight_validate(raw_task: Any) -> Tuple[bool, str, List[str]]:
    """Defensively handles None, wrong types, empty inputs, or oversized payloads."""
    plan: List[str] = []

    # Type validation
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

    # Step 3: Domain Logic (Extendable by use-case specific prompt)
    plan.append(f"Processing sanitized task: {normalized_task[:60]}...")
    
    # Calculate baseline scores (To be customized per usecase in phase 2)
    confidence_score = 0.95
    risk_score = 0.10
    escalated = False

    result = {
        "status": "PROCESSED",
        "task_summary": normalized_task[:100],
        "confidence": confidence_score,
        "risk": risk_score,
    }

    # Step 4: Tamper-Evident Audit Log
    rec_hash = log_audit_entry(
        task=normalized_task,
        confidence_score=confidence_score,
        risk_score=risk_score,
        escalated=escalated,
        decision="SUCCESSFUL_TRIAGE",
    )
    plan.append(f"Audit Trail: Chained to SHA-256 record {rec_hash[:12]}...")

    return {
        "plan": plan,
        "result": result,
        "escalated": escalated,
    }
