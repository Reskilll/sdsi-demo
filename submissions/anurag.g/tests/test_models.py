"""Test models: parsing, validation, error handling."""

import pytest
from scheduler.models import load_graph, GraphLoadError, JobGraph


def test_load_from_dict():
    g = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
    ]})
    assert len(g.jobs) == 2
    assert g.get("A").duration == 1.0


def test_load_from_file(tmp_path):
    import json
    f = tmp_path / "test.json"
    f.write_text(json.dumps({"jobs": [{"id": "X", "duration": 7}]}))
    g = load_graph(f)
    assert g.get("X").duration == 7.0


def test_load_from_json_string():
    g = load_graph('{"jobs": [{"id": "Y", "duration": 3}]}')
    assert g.get("Y").duration == 3.0


def test_nonexistent_file():
    with pytest.raises(GraphLoadError, match="File not found"):
        load_graph("/nonexistent/path.json")


def test_invalid_json():
    with pytest.raises(GraphLoadError, match="Invalid JSON"):
        load_graph("not json")


def test_not_a_dict():
    with pytest.raises(GraphLoadError, match="object"):
        load_graph({"jobs": "not a list"})


def test_jobs_not_list():
    with pytest.raises(GraphLoadError, match="must be a list"):
        load_graph({"jobs": "nope"})


def test_missing_id():
    with pytest.raises(GraphLoadError, match="id"):
        load_graph({"jobs": [{"duration": 1}]})


def test_empty_id():
    with pytest.raises(GraphLoadError, match="id"):
        load_graph({"jobs": [{"id": "  ", "duration": 1}]})


def test_duplicate_id():
    with pytest.raises(GraphLoadError, match="Duplicate"):
        load_graph({"jobs": [
            {"id": "A", "duration": 1},
            {"id": "A", "duration": 2},
        ]})


def test_missing_duration():
    with pytest.raises(GraphLoadError, match="duration"):
        load_graph({"jobs": [{"id": "A"}]})


def test_non_numeric_duration():
    with pytest.raises(GraphLoadError, match="number"):
        load_graph({"jobs": [{"id": "A", "duration": "slow"}]})


def test_zero_duration():
    with pytest.raises(GraphLoadError, match="positive"):
        load_graph({"jobs": [{"id": "A", "duration": 0}]})


def test_negative_duration():
    with pytest.raises(GraphLoadError, match="positive"):
        load_graph({"jobs": [{"id": "A", "duration": -5}]})


def test_depends_on_string_normalized():
    g = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 2, "dependsOn": "A"},
    ]})
    assert g.get("B").depends_on == ["A"]


def test_bad_depends_on_type():
    with pytest.raises(GraphLoadError, match="dependsOn"):
        load_graph({"jobs": [{"id": "A", "duration": 1, "dependsOn": 42}]})


def test_depends_on_list_with_non_strings():
    with pytest.raises(GraphLoadError, match="dependsOn"):
        load_graph({"jobs": [{"id": "A", "duration": 1, "dependsOn": ["B", 1]}]})


def test_empty_graph():
    g = load_graph({"jobs": []})
    assert len(g.jobs) == 0


def test_job_graph_contains():
    g = load_graph({"jobs": [{"id": "A", "duration": 1}]})
    assert "A" in g
    assert "B" not in g


def test_job_graph_get_missing():
    g = load_graph({"jobs": [{"id": "A", "duration": 1}]})
    with pytest.raises(KeyError):
        g.get("B")


def test_dependents_tracking():
    g = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 3, "dependsOn": ["A"]},
    ]})
    assert set(g.dependents_of("A")) == {"B", "C"}
    assert g.dependents_of("B") == []