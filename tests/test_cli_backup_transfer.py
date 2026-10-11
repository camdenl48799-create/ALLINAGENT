from pathlib import Path
import json
import sys

from allinagent.cli import main


def test_backup_create_and_verify_cli(tmp_path: Path, monkeypatch, capsys):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".allinagent-memory.json").write_text('[{"prompt":"hello"}]', encoding="utf-8")
    backups = tmp_path / "backups"
    monkeypatch.setattr(sys, "argv", ["allinagent", "--workspace", str(workspace), "--backup-dir", str(backups), "backup", "create"])
    assert main() == 0
    created = list(backups.glob("allinagent-backup-*.zip"))
    assert len(created) == 1
    monkeypatch.setattr(sys, "argv", ["allinagent", "--workspace", str(workspace), "backup", "verify", str(created[0])])
    assert main() == 0
    assert '"valid": true' in capsys.readouterr().out.lower()


def test_export_import_cli(tmp_path: Path, monkeypatch, capsys):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / ".allinagent-memory.json").write_text('[{"prompt":"portable"}]', encoding="utf-8")
    package = tmp_path / "workspace.zip"
    monkeypatch.setattr(sys, "argv", ["allinagent", "--workspace", str(source), "export", str(package)])
    assert main() == 0
    monkeypatch.setattr(sys, "argv", ["allinagent", "--workspace", str(target), "import", str(package)])
    assert main() == 0
    assert json.loads((target / ".allinagent-memory.json").read_text(encoding="utf-8"))[0]["prompt"] == "portable"
