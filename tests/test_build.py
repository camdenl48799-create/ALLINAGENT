"""Tests for Windows executable build orchestration."""
from pathlib import Path

from allinagent.build import WindowsBuilder


def test_detect_python(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    result = WindowsBuilder(tmp_path).detect()
    assert result["type"] == "python"
    assert result["entry"] == "main.py"


def test_detect_dotnet(tmp_path: Path):
    (tmp_path / "Demo.csproj").write_text("<Project />\n", encoding="utf-8")
    result = WindowsBuilder(tmp_path).detect()
    assert result["type"] == "dotnet"
    assert result["entry"] == "Demo.csproj"


def test_unknown_project(tmp_path: Path):
    assert WindowsBuilder(tmp_path).detect()["type"] == "unknown"


def test_build_requires_shell_permission(tmp_path: Path):
    assert "BUILD DENIED" in WindowsBuilder(tmp_path).build()


def test_build_dry_run_does_not_execute(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    result = WindowsBuilder(tmp_path, allow_shell=True, dry_run=True).build()
    assert "BUILD BLOCKED" in result
