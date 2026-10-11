from pathlib import Path
import json
import zipfile

import pytest

from allinagent.transfer import export_workspace, inspect_package, import_workspace


def test_export_import_round_trip_and_source_preservation(tmp_path: Path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / ".allinagent-memory.json").write_text('[{"prompt":"hello","response":"world"}]', encoding="utf-8")
    (source / ".allinagent" ).mkdir()
    (source / ".allinagent" / "project.json").write_text('{"name":"demo","purpose":"test"}', encoding="utf-8")
    before = (source / ".allinagent-memory.json").read_bytes()
    package = tmp_path / "export.zip"
    result = export_workspace(source, package)
    assert result["file_count"] == 2
    assert inspect_package(package)["valid"] is True
    imported = import_workspace(target, package)
    assert imported["source_unchanged"] is True
    assert (target / ".allinagent-memory.json").exists()
    assert (source / ".allinagent-memory.json").read_bytes() == before


def test_import_merges_unique_memory_and_preserves_project_conflicts(tmp_path: Path, monkeypatch):
    import allinagent.backup.store as backup_store
    monkeypatch.setattr(backup_store, "_default_root", lambda: tmp_path / "backups")
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / ".allinagent-memory.json").write_text('[{"prompt":"one"},{"prompt":"two"}]', encoding="utf-8")
    (source / ".allinagent").mkdir()
    (source / ".allinagent" / "project.json").write_text('{"name":"incoming","purpose":"new"}', encoding="utf-8")
    (target / ".allinagent-memory.json").write_text('[{"prompt":"one"}]', encoding="utf-8")
    (target / ".allinagent").mkdir()
    (target / ".allinagent" / "project.json").write_text('{"name":"existing","local":true}', encoding="utf-8")
    package = tmp_path / "export.zip"
    export_workspace(source, package)
    result = import_workspace(target, package)
    memory = json.loads((target / ".allinagent-memory.json").read_text(encoding="utf-8"))
    project = json.loads((target / ".allinagent" / "project.json").read_text(encoding="utf-8"))
    assert len(memory) == 2
    assert project["name"] == "existing"
    assert project["purpose"] == "new"
    assert result["conflicts"] == [".allinagent-memory.json", ".allinagent/project.json"]


def test_invalid_package_does_not_mutate_workspace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    existing = workspace / ".allinagent-memory.json"
    existing.write_text('[{"prompt":"keep"}]', encoding="utf-8")
    package = tmp_path / "invalid.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("manifest.json", '{"format_version": 77, "files": {}}')
    with pytest.raises(ValueError):
        import_workspace(workspace, package, conflict="replace")
    assert existing.read_text(encoding="utf-8") == '[{"prompt":"keep"}]'
