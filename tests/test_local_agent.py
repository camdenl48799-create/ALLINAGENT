"""Focused regression tests for ALLINAGENT's local tool safety."""
from __future__ import annotations

from pathlib import Path

import pytest

from allinagent.local_brain import LocalBrain
from allinagent.tools import WorkspaceTools, WorkspaceViolation


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n# TODO: test\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\nALLINAGENT\n", encoding="utf-8")
    (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")
    return tmp_path


def test_read_file_is_local(workspace: Path) -> None:
    tools = WorkspaceTools(workspace)
    assert "hello" in tools.read_file("src/main.py")


def test_missing_file_is_reported(workspace: Path) -> None:
    result = WorkspaceTools(workspace).read_file("missing.py")
    assert result.startswith("READ: file does not exist")


def test_path_escape_is_rejected(workspace: Path) -> None:
    tools = WorkspaceTools(workspace)
    with pytest.raises(WorkspaceViolation):
        tools.read_file("../outside.txt")


def test_absolute_path_escape_is_rejected(workspace: Path) -> None:
    tools = WorkspaceTools(workspace)
    outside = workspace.parent / "outside.txt"
    with pytest.raises(WorkspaceViolation):
        tools.read_file(str(outside))


def test_search_finds_case_insensitive_text(workspace: Path) -> None:
    result = WorkspaceTools(workspace).search_text("todo")
    assert "src/main.py:2" in result


def test_binary_files_can_be_skipped(workspace: Path) -> None:
    result = WorkspaceTools(workspace).search_text("hello")
    assert "data.bin" not in result


def test_writes_are_denied_by_default(workspace: Path) -> None:
    tools = WorkspaceTools(workspace)
    result = tools.write_file("new.txt", "hello")
    assert "WRITE DENIED" in result
    assert not (workspace / "new.txt").exists()


def test_dry_run_blocks_write(workspace: Path) -> None:
    tools = WorkspaceTools(workspace, allow_write=True, dry_run=True)
    result = tools.write_file("new.txt", "hello")
    assert "WRITE BLOCKED" in result
    assert not (workspace / "new.txt").exists()


def test_enabled_write_is_scoped(workspace: Path) -> None:
    tools = WorkspaceTools(workspace, allow_write=True)
    result = tools.write_file("src/new.py", "x = 1\n")
    assert "WRITE OK" in result
    assert (workspace / "src/new.py").read_text(encoding="utf-8") == "x = 1\n"


def test_shell_is_denied_by_default(workspace: Path) -> None:
    result = WorkspaceTools(workspace).run_shell("echo test")
    assert "SHELL DENIED" in result


def test_dry_run_blocks_shell(workspace: Path) -> None:
    tools = WorkspaceTools(workspace, allow_shell=True, dry_run=True)
    result = tools.run_shell("echo test")
    assert "SHELL BLOCKED" in result


def test_shell_can_run_when_explicitly_enabled(workspace: Path) -> None:
    tools = WorkspaceTools(workspace, allow_shell=True)
    result = tools.run_shell("python -c \"print('agent-test')\"")
    assert "agent-test" in result


def test_project_summary_reports_files(workspace: Path) -> None:
    result = WorkspaceTools(workspace).project_summary()
    assert "src/main.py" in result
    assert "README.md" in result


def test_storage_report_is_read_only(workspace: Path) -> None:
    before = sorted(p.name for p in workspace.iterdir())
    result = WorkspaceTools(workspace).storage_report()
    after = sorted(p.name for p in workspace.iterdir())
    assert "SAFE MODE" in result
    assert before == after


def test_list_dir_reports_directory(workspace: Path) -> None:
    result = WorkspaceTools(workspace).list_dir("src")
    assert "main.py" in result


def test_tree_reports_nested_files(workspace: Path) -> None:
    result = WorkspaceTools(workspace).tree(".", depth=2)
    assert "src/" in result
    assert "main.py" in result


def test_extension_report_counts_python(workspace: Path) -> None:
    result = WorkspaceTools(workspace).extension_report()
    assert ".py: 1" in result


def test_diagnostics_exposes_safety_state(workspace: Path) -> None:
    result = WorkspaceTools(workspace).diagnostics()
    assert "path traversal protection: active" in result


def test_local_brain_handles_identity(workspace: Path) -> None:
    brain = LocalBrain(WorkspaceTools(workspace))
    assert brain.can_handle("who are you")
    assert "ALLINAGENT" in brain.run("who are you")


def test_local_brain_handles_summary(workspace: Path) -> None:
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("analyze project")
    assert "PROJECT SUMMARY" in result


def test_local_brain_handles_search(workspace: Path) -> None:
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("find TODO")
    assert "src/main.py:2" in result


def test_local_brain_explains_unknown_requests_without_network(workspace: Path) -> None:
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("invent a quantum compiler")
    assert "No request was sent off-machine" in result


def test_local_brain_builds_safe_read_plan(workspace: Path) -> None:
    brain = LocalBrain(WorkspaceTools(workspace))
    steps = brain.build_plan("read file README.md")
    assert len(steps) == 1
    assert "Read" in steps[0].label


def test_local_brain_available_commands_are_stable(workspace: Path) -> None:
    commands = LocalBrain(WorkspaceTools(workspace)).available_commands()
    assert "who are you" in commands
    assert "read file <path>" in commands
