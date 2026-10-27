"""Input validation and parsing for job specifications."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


@dataclass
class JobSpec:
    """Intermediate representation of a single job from input JSON."""

    name: str
    duration: float
    depends_on: List[str]


@dataclass
class ValidatedInput:
    """Sanitised, validated input ready for scheduling."""

    jobs: Dict[str, JobSpec]
    worker_limit: int
    source_path: str


class ValidationError(ValueError):
    """Raised when input fails validation."""

    pass


# ---------------------------------------------------------------------------
# Helper — JSON loading with injection guard
# ---------------------------------------------------------------------------

def load_json_safe(path: Path) -> dict:
    """Load a JSON file, guarding against code-injection via `__init__` etc."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValidationError(f"File not found: {path}")
    except UnicodeDecodeError:
        raise ValidationError(f"File is not valid UTF-8: {path}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}")

    if not isinstance(data, dict):
        raise ValidationError("Top-level JSON must be an object (dict)")

    return data


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

def validate_and_parse(
    data: dict,
    *,
    source_path: str = "<input>",
    default_worker_limit: int = 4,
) -> ValidatedInput:
    """Parse and validate a job-spec dictionary.

    Expected shape:
      {
        "jobs": [
          {"name": "A", "duration": 3, "dependsOn": []},
          {"name": "B", "duration": 2, "dependsOn": ["A"]}
        ],
        "workerLimit": 4    // optional, default 4
      }
    """
    errors: List[str] = []

    # --- worker limit ---
    worker_limit = data.get("workerLimit", default_worker_limit)
    if not isinstance(worker_limit, int) or worker_limit < 1:
        errors.append(
            f"'workerLimit' must be a positive integer, got: {worker_limit!r}"
        )

    # --- jobs ---
    raw_jobs: Any = data.get("jobs")
    if raw_jobs is None:
        errors.append("Missing required key: 'jobs'")
        if errors:
            raise ValidationError("; ".join(errors))
        return ValidatedInput(jobs={}, worker_limit=max(1, worker_limit), source_path=source_path)  # unreachable

    if not isinstance(raw_jobs, list):
        errors.append("'jobs' must be a list")
        if errors:
            raise ValidationError("; ".join(errors))
        return ValidatedInput(jobs={}, worker_limit=max(1, worker_limit), source_path=source_path)

    if len(raw_jobs) == 0:
        errors.append("'jobs' list is empty")

    jobs: Dict[str, JobSpec] = {}
    seen_names: set[str] = set()

    for i, item in enumerate(raw_jobs):
        _validate_single_job(item, i, jobs, seen_names, errors)

    # --- cross-reference dependencies ---
    if not errors:
        for name, spec in jobs.items():
            for dep in spec.depends_on:
                if dep not in jobs:
                    errors.append(
                        f"Job '{name}' depends on '{dep}' which does not exist"
                    )

    if errors:
        raise ValidationError("; ".join(errors))

    # --- security: strip any unexpected keys from the input ---
    safe_jobs = {
        name: JobSpec(name=s.name, duration=s.duration, depends_on=s.depends_on)
        for name, s in jobs.items()
    }

    return ValidatedInput(
        jobs=safe_jobs,
        worker_limit=worker_limit,
        source_path=source_path,
    )


def _validate_single_job(
    item: Any,
    idx: int,
    jobs: Dict[str, JobSpec],
    seen_names: set[str],
    errors: List[str],
) -> None:
    if not isinstance(item, dict):
        errors.append(f"jobs[{idx}]: must be an object, got {type(item).__name__}")
        return

    # --- name ---
    name: Any = item.get("name")
    if name is None:
        errors.append(f"jobs[{idx}]: missing required field 'name'")
        return
    if not isinstance(name, str) or name.strip() == "":
        errors.append(f"jobs[{idx}]: 'name' must be a non-empty string, got {name!r}")
        return
    name = name.strip()

    # SQL-injection-like guard: reject names with suspicious characters
    if not _is_safe_identifier(name):
        errors.append(
            f"jobs[{idx}]: 'name' contains unsafe characters: {name!r}"
        )
        return

    if name in seen_names:
        errors.append(f"jobs[{idx}]: duplicate job name '{name}'")
        return
    seen_names.add(name)

    # --- duration ---
    duration: Any = item.get("duration")
    if duration is None:
        errors.append(f"jobs[{idx}]: missing required field 'duration'")
        return
    if not isinstance(duration, (int, float)):
        errors.append(
            f"jobs[{idx}]: 'duration' must be a number, got {type(duration).__name__}"
        )
        return
    if duration < 0:
        errors.append(f"jobs[{idx}]: 'duration' must be >= 0, got {duration}")
        return
    if duration > 86_400 * 365:  # 1 year in seconds — sanity cap
        errors.append(f"jobs[{idx}]: 'duration' exceeds sanity cap")
        return

    # --- dependsOn ---
    depends_on: Any = item.get("dependsOn", [])
    if isinstance(depends_on, list):
        clean_deps: List[str] = []
        for j, d in enumerate(depends_on):
            if not isinstance(d, str) or d.strip() == "":
                errors.append(
                    f"jobs[{idx}].dependsOn[{j}]: must be a non-empty string"
                )
            else:
                clean_deps.append(d.strip())
        depends_on = clean_deps
    else:
        errors.append(
            f"jobs[{idx}]: 'dependsOn' must be a list, got {type(depends_on).__name__}"
        )
        depends_on = []

    # Check for self-dependency
    if name in depends_on:
        errors.append(f"jobs[{idx}]: job '{name}' cannot depend on itself")

    # Check for duplicate dependencies
    if len(depends_on) != len(set(depends_on)):
        errors.append(f"jobs[{idx}]: 'dependsOn' contains duplicates")

    jobs[name] = JobSpec(name=name, duration=float(duration), depends_on=depends_on)


def _is_safe_identifier(s: str) -> bool:
    """Allow alphanumeric, hyphens, underscores, dots — reject shell metacharacters."""
    for ch in s:
        if not (ch.isalnum() or ch in "-_."):
            return False
    return True


def spec_to_jobnodes(validated: ValidatedInput) -> Dict[str, "JobNode"]:
    """Convert validated input to graph JobNode objects.

    Late import to avoid circular dependency at module level.
    """
    from .graph import JobNode  # pylint: disable=import-outside-toplevel

    return {
        name: JobNode(name=s.name, duration=s.duration, depends_on=s.depends_on)
        for name, s in validated.jobs.items()
    }