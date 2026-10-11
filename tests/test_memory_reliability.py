from pathlib import Path
import json

import pytest

from allinagent.memory import LocalMemory, MAX_ENTRIES
from allinagent.project import ProjectMemory


def test_legacy_memory_and_recent_limits_are_preserved(tmp_path: Path):
    path = tmp_path / ".allinagent-memory.json"
    legacy = [{"timestamp": str(i), "prompt": f"p{i}", "response": f"r{i}"} for i in range(12)]
    path.write_text(json.dumps(legacy), encoding="utf-8")
    memory = LocalMemory(tmp_path)
    assert memory._load() == legacy
    assert [item["prompt"] for item in memory.recent(3)] == ["p9", "p10", "p11"]


def test_memory_save_caps_entries(tmp_path: Path):
    memory = LocalMemory(tmp_path)
    memory._save([{"prompt": str(i), "response": "ok"} for i in range(MAX_ENTRIES + 3)])
    assert len(json.loads(memory.path.read_text(encoding="utf-8"))) == MAX_ENTRIES


def test_malformed_memory_is_reported_and_preserved(tmp_path: Path):
    path = tmp_path / ".allinagent-memory.json"
    original = b'{"prompt": "unfinished"'
    path.write_bytes(original)
    memory = LocalMemory(tmp_path)
    assert memory._load() == []
    assert memory.load_error
    assert "warning" in memory.status().lower()
    with pytest.raises(OSError):
        memory.remember("private text", "private response")
    assert path.read_bytes() == original
    assert "private text" not in memory.status()


def test_atomic_replace_failure_preserves_previous_memory(tmp_path: Path, monkeypatch):
    import allinagent._persistence as persistence

    path = tmp_path / ".allinagent-memory.json"
    path.write_text('[{"prompt":"old","response":"valid"}]', encoding="utf-8")

    def fail_replace(_source, _destination):
        raise OSError("replace failed")

    monkeypatch.setattr(persistence.os, "replace", fail_replace)
    with pytest.raises(OSError):
        LocalMemory(tmp_path).remember("new", "entry")
    assert json.loads(path.read_text(encoding="utf-8"))[0]["prompt"] == "old"
    assert not list(tmp_path.glob(".allinagent-memory.json.*.tmp"))


def test_project_metadata_is_not_overwritten_when_malformed(tmp_path: Path):
    project = ProjectMemory(tmp_path)
    project.project_dir.mkdir()
    original = b"{broken"
    project.path.write_bytes(original)
    with pytest.raises(OSError):
        project.create("demo", "test")
    assert project.path.read_bytes() == original
    assert "warning" in project.status().lower()
