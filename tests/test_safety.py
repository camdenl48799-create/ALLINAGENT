"""Tests for safety guardrails, memory controls, and error recovery."""
from __future__ import annotations

from pathlib import Path

import pytest

from allinagent.tools import WorkspaceTools
from allinagent.agent import Agent
from allinagent.config import Config


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return tmp_path


# --- Shell guardrails ---


def test_shell_blocks_rm_rf_root(workspace: Path):
    tools = WorkspaceTools(workspace, allow_shell=True)
    result = tools.run_shell("rm -rf /")
    assert "DENIED" in result


def test_shell_blocks_rm_rf_home(workspace: Path):
    tools = WorkspaceTools(workspace, allow_shell=True)
    result = tools.run_shell("rm -rf ~")
    assert "DENIED" in result


def test_shell_blocks_mkfs(workspace: Path):
    tools = WorkspaceTools(workspace, allow_shell=True)
    result = tools.run_shell("mkfs.ext4 /dev/sda1")
    assert "DENIED" in result


def test_shell_blocks_shutdown(workspace: Path):
    tools = WorkspaceTools(workspace, allow_shell=True)
    result = tools.run_shell("shutdown now")
    assert "DENIED" in result


def test_shell_allows_safe_command(workspace: Path):
    tools = WorkspaceTools(workspace, allow_shell=True)
    result = tools.run_shell("echo hello")
    assert "DENIED" not in result


# --- Protected file overwrite ---


def test_write_blocked_on_protected_config(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    result = tools.write_file("pyproject.toml", "new content")
    assert "DENIED" in result
    assert "protected" in result.lower()


def test_write_blocked_on_gitignore(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    (workspace / ".gitignore").write_text("old\n", encoding="utf-8")
    result = tools.write_file(".gitignore", "new content")
    assert "DENIED" in result


def test_write_allows_new_unprotected_file(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    result = tools.write_file("newfile.txt", "hello")
    assert "WRITE OK" in result


def test_edit_file_allows_targeted_change_to_config(workspace: Path):
    """edit_file should work on config files since it's a targeted change, not a full overwrite."""
    tools = WorkspaceTools(workspace, allow_write=True)
    (workspace / "config.txt").write_text("key=old_value\n", encoding="utf-8")
    result = tools.edit_file("config.txt", "old_value", "new_value")
    assert "EDIT OK" in result


# --- Protected file deletion ---


def test_delete_blocked_on_pyproject(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    result = tools.delete_file("pyproject.toml", confirm=True)
    assert "DENIED" in result


def test_delete_blocked_on_env(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    (workspace / ".env").write_text("KEY=value\n", encoding="utf-8")
    result = tools.delete_file(".env", confirm=True)
    assert "DENIED" in result


def test_delete_blocked_on_project_memory(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    (workspace / ".allinagent").mkdir()
    (workspace / ".allinagent" / "project.json").write_text("{}", encoding="utf-8")
    result = tools.delete_file(".allinagent/project.json", confirm=True)
    assert "DENIED" in result


# --- Memory controls ---


def test_memory_disabled_does_not_store(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.memory_enabled = False
    agent.run("who are you")
    entries = agent.memory._load()
    assert len(entries) == 0


def test_memory_enabled_stores_conversation(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.memory_enabled = True
    agent.run("who are you")
    entries = agent.memory._load()
    assert len(entries) >= 1


def test_memory_view_shows_entries(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("who are you")
    context = agent.memory.context()
    assert "ALLINAGENT" in context


def test_no_memory_flag_in_argparser():
    from allinagent.cli import build_parser
    args = build_parser().parse_args(["--no-memory", "test"])
    assert args.no_memory is True


# --- Project memory lazy creation ---


def test_project_memory_does_not_create_dir_on_read(workspace: Path):
    from allinagent.project import ProjectMemory
    pm = ProjectMemory(workspace)
    # Just loading should not create .allinagent/
    pm._load()
    assert not (workspace / ".allinagent").exists()


def test_project_memory_creates_dir_on_save(workspace: Path):
    from allinagent.project import ProjectMemory
    pm = ProjectMemory(workspace)
    pm.create(name="test", purpose="testing", kind="website")
    assert (workspace / ".allinagent" / "project.json").exists()


# --- Payment env example ---


def test_payment_creates_env_example(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    result = agent.run("create env example")
    assert "env.example" in result.lower() or ".env.example" in result.lower()
    assert (workspace / ".env.example").exists()


def test_payment_env_example_without_write(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("create env example")
    assert "permission" in result.lower() or "denied" in result.lower()


def test_payment_guidance_shown_for_selling(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("I want to sell my game")
    assert "PAYMENT" in result or "payment" in result.lower()


# --- Follow-up file tracking ---


def test_followup_adds_file_to_project_memory(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    agent.run("add a games page")
    data = agent.project._load()
    files = data.get("important_files", [])
    file_paths = [f["path"] for f in files]
    # games.html should be tracked
    assert any("games.html" in p for p in file_paths)
