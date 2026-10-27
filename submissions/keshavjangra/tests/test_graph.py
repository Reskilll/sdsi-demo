"""Tests for M1 – DAG validation (cycles and missing dependencies)."""

import pytest

from scheduler.graph import DAG, Job


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_valid_dag_parses_without_error():
    dag = DAG.from_dicts([
        {"id": "A", "duration": 1, "dependsOn": []},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 3, "dependsOn": ["B"]},
    ])
    assert len(dag) == 3
    assert dag.roots() == ["A"]
    assert dag.leaves() == ["C"]


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

def test_simple_cycle_detected():
    with pytest.raises(ValueError, match="Cycle detected"):
        DAG.from_dicts([
            {"id": "A", "duration": 1, "dependsOn": ["B"]},
            {"id": "B", "duration": 1, "dependsOn": ["A"]},
        ])


def test_three_node_cycle_with_path():
    with pytest.raises(ValueError) as exc:
        DAG.from_dicts([
            {"id": "X", "duration": 1, "dependsOn": ["Y"]},
            {"id": "Y", "duration": 1, "dependsOn": ["Z"]},
            {"id": "Z", "duration": 1, "dependsOn": ["X"]},
        ])
    msg = str(exc.value)
    assert "Cycle detected" in msg
    # The reported path should contain all three nodes
    for n in ("X", "Y", "Z"):
        assert n in msg


def test_self_loop():
    with pytest.raises(ValueError, match="Cycle detected"):
        DAG.from_dicts([
            {"id": "A", "duration": 1, "dependsOn": ["A"]},
        ])


def test_cycle_in_subset():
    """Cycle among B→C→B while A is clean."""
    with pytest.raises(ValueError):
        DAG.from_dicts([
            {"id": "A", "duration": 1, "dependsOn": []},
            {"id": "B", "duration": 1, "dependsOn": ["A", "C"]},
            {"id": "C", "duration": 1, "dependsOn": ["B"]},
        ])


# ---------------------------------------------------------------------------
# Missing dependencies
# ---------------------------------------------------------------------------

def test_missing_dependency():
    with pytest.raises(ValueError, match="Missing dependencies"):
        DAG.from_dicts([
            {"id": "A", "duration": 1, "dependsOn": ["GHOST"]},
        ])


def test_missing_dependency_message_names_job():
    with pytest.raises(ValueError) as exc:
        DAG.from_dicts([
            {"id": "A", "duration": 5, "dependsOn": ["Z"]},
        ])
    msg = str(exc.value)
    assert "A" in msg
    assert "Z" in msg


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_missing_id_key():
    with pytest.raises(ValueError, match="missing required key 'id'"):
        DAG.from_dicts([{"duration": 1, "dependsOn": []}])


def test_missing_duration_key():
    with pytest.raises(ValueError, match="missing required key 'duration'"):
        DAG.from_dicts([{"id": "A", "dependsOn": []}])


def test_negative_duration():
    with pytest.raises(ValueError, match="non-negative"):
        DAG.from_dicts([{"id": "A", "duration": -3, "dependsOn": []}])


def test_depends_on_not_a_list():
    with pytest.raises(ValueError, match="dependsOn must be a list"):
        DAG.from_dicts([{"id": "A", "duration": 1, "dependsOn": "B"}])


def test_depends_on_non_string_entry():
    with pytest.raises(ValueError, match="dependsOn entries must be strings"):
        DAG.from_dicts([{"id": "A", "duration": 1, "dependsOn": [123]}])


def test_duplicate_job_id():
    with pytest.raises(ValueError, match="Duplicate job id"):
        DAG.from_dicts([
            {"id": "A", "duration": 1, "dependsOn": []},
            {"id": "A", "duration": 2, "dependsOn": []},
        ])


def test_from_json_file_with_object_not_array(tmp_path):
    """from_json_file rejects a JSON object (not array)."""
    f = tmp_path / "bad.json"
    f.write_text('{"id": "A"}')
    with pytest.raises(ValueError, match="Expected a JSON array"):
        DAG.from_json_file(f)