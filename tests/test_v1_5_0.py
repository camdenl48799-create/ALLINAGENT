from pathlib import Path

from allinagent import __version__
from allinagent.game_dev import inspect_game_project
from allinagent.model_router import choose_profile
from allinagent.prompt_contract import build_contract
from allinagent.security import SecurityScanner
from allinagent.storage_health import snapshot


def test_version():
    assert __version__ == "1.5.0"


def test_prompt_contract_keeps_explicit_requirements():
    c = build_contract("Build a game.\n- Add a pause menu.\n- Add C++ networking.")
    assert len(c.requirements) >= 3
    assert any("pause menu" in r.text for r in c.requirements)


def test_model_router_selects_game_profile():
    assert choose_profile("make a Unity game in C#").name == "allinone-game"


def test_game_project_detection(tmp_path: Path):
    (tmp_path / "project.godot").write_text("", encoding="utf-8")
    (tmp_path / "player.gd").write_text("", encoding="utf-8")
    report = inspect_game_project(tmp_path)
    assert "Godot" in report.engines


def test_security_scanner_does_not_quarantine_outside_workspace(tmp_path: Path):
    scanner = SecurityScanner(tmp_path)
    assert "DENIED" in scanner.quarantine_file(str(tmp_path.parent / "outside.txt"))


def test_security_scanner_detects_suspicious_pattern(tmp_path: Path):
    p = tmp_path / "sample.ps1"
    p.write_text("powershell -EncodedCommand abc", encoding="utf-8")
    finding = SecurityScanner(tmp_path).scan_file(p)
    assert finding is not None
    assert finding.confidence >= 20


def test_storage_snapshot(tmp_path: Path):
    s = snapshot(tmp_path)
    assert s.total_bytes > 0
    assert 0 <= s.free_percent <= 100
