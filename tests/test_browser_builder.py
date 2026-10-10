"""Tests for the v1.8.0 desktop browser builder."""
from pathlib import Path

from allinagent.browser_builder import BrowserBuilder
from allinagent.tools import WorkspaceTools


def test_browser_builder_plan_only_does_not_write(tmp_path: Path):
    builder = BrowserBuilder(WorkspaceTools(tmp_path, allow_write=False))
    result = builder.build("make me a browser")
    assert "PLAN ONLY" in result
    assert not (tmp_path / "my-browser").exists()


def test_browser_builder_creates_real_qt_webengine_scaffold(tmp_path: Path):
    tools = WorkspaceTools(tmp_path, allow_write=True)
    result = BrowserBuilder(tools).build("make me a browser called Vrax-Z Browser")
    project = tmp_path / "vrax-z-browser"
    assert "BROWSER BUILDER COMPLETE" in result
    assert (project / "main.py").exists()
    assert (project / "requirements.txt").read_text(encoding="utf-8").strip() == "PySide6>=6.6"
    source = (project / "main.py").read_text(encoding="utf-8")
    assert "QWebEngineView" in source
    assert "QTabWidget" in source
    assert "Ctrl+T" in source
    assert "QWebEngineView" in source
