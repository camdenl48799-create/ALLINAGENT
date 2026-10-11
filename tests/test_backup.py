from pathlib import Path
import json
import zipfile

import pytest

from allinagent.backup import create_backup, list_backups, verify_backup, restore_backup


def test_backup_manifest_and_verification(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".allinagent-memory.json").write_text(json.dumps([{"prompt": "hi", "response": "there"}]), encoding="utf-8")
    backup = create_backup(workspace, tmp_path / "backups")
    result = verify_backup(backup)
    assert result["valid"] is True
    assert result["format_version"] == 1
    assert result["file_count"] == 1
    assert result["record_count"] == 1
    assert list_backups(tmp_path / "backups")[0]["valid"] is True


def test_restore_refuses_to_overwrite_without_replace(tmp_path: Path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / ".allinagent-memory.json").write_text('[{"prompt":"old"}]', encoding="utf-8")
    backup = create_backup(source, tmp_path / "backups")
    destination = target / ".allinagent-memory.json"
    destination.write_text('[{"prompt":"new"}]', encoding="utf-8")
    with pytest.raises(FileExistsError):
        restore_backup(target, backup)
    assert json.loads(destination.read_text(encoding="utf-8"))[0]["prompt"] == "new"


def test_corrupt_backup_is_rejected_without_changes(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".allinagent-memory.json").write_text('[{"prompt":"safe"}]', encoding="utf-8")
    corrupt = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(corrupt, "w") as archive:
        archive.writestr("manifest.json", '{"format_version": 999, "files": {}}')
    before = (workspace / ".allinagent-memory.json").read_bytes()
    with pytest.raises(ValueError):
        restore_backup(workspace, corrupt, replace=True)
    assert (workspace / ".allinagent-memory.json").read_bytes() == before


def test_backup_digest_detects_tampering(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".allinagent-memory.json").write_text("[]", encoding="utf-8")
    backup = create_backup(workspace, tmp_path / "backups")
    changed = tmp_path / "changed.zip"
    with zipfile.ZipFile(backup, "r") as source, zipfile.ZipFile(changed, "w") as target:
        for name in source.namelist():
            target.writestr(name, b'[{}]' if name == ".allinagent-memory.json" else source.read(name))
    with pytest.raises(ValueError):
        verify_backup(changed)
