"""Tests for ALLINAGENT v1.1.0 creation system, project memory, file ops, and validators."""
from __future__ import annotations

from pathlib import Path

import pytest

from allinagent.tools import WorkspaceTools, WorkspaceViolation
from allinagent.website_builder import WebsiteBuilder, CreationSpec
from allinagent.creator import Creator
from allinagent.project import ProjectMemory
from allinagent.validators import Validators
from allinagent.guardrails import Guardrails, RiskLevel
from allinagent.local_brain import LocalBrain
from allinagent.agent import Agent
from allinagent.config import Config


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n# TODO: test\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\nALLINAGENT\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def write_workspace(tmp_path: Path) -> Path:
    (tmp_path / "existing.txt").write_text("hello world", encoding="utf-8")
    return tmp_path


# --- Creator / Website Builder ---


def test_creator_detects_website_request(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    creator = Creator(tools)
    assert creator.can_handle("make me a website")
    assert creator.can_handle("create a game")
    assert creator.can_handle("build me a script")


def test_creator_plan_only_without_write_permission(workspace: Path):
    tools = WorkspaceTools(workspace)
    creator = Creator(tools)
    result = creator.run("make me a dark gaming website", allow_write=False)
    assert "PLAN ONLY" in result
    assert "index.html" in result
    assert not (workspace / "dark-gaming").exists()


def test_creator_creates_website_with_write_permission(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    creator = Creator(tools)
    result = creator.run("make me a dark gaming website", allow_write=True)
    assert "CREATION COMPLETE" in result
    assert (workspace / "dark-gaming-website" / "index.html").exists()
    assert (workspace / "dark-gaming-website" / "styles.css").exists()
    assert (workspace / "dark-gaming-website" / "script.js").exists()
    assert (workspace / "dark-gaming-website" / "README.md").exists()


def test_website_builder_parses_theme(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = WebsiteBuilder(tools)
    spec = builder.parse_prompt("make me a dark gaming website")
    assert spec.kind == "website"
    assert spec.theme in ("dark", "gaming")
    assert spec.color_scheme == "dark"


def test_website_builder_parses_game_name(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = WebsiteBuilder(tools)
    spec = builder.parse_prompt("make me a game called DOG GO")
    assert spec.kind == "game"
    assert "dog" in spec.name.lower()


def test_website_builder_creates_real_files(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = WebsiteBuilder(tools)
    spec = CreationSpec(kind="website", name="test-site", theme="dark", color_scheme="dark")
    created = builder.build_website(spec)
    assert len(created) >= 4
    assert any("index.html" in f for f in created)
    assert any("styles.css" in f for f in created)
    html = tools.read_file("test-site/index.html")
    assert "<!DOCTYPE html>" in html or "<html" in html


def test_followup_modifies_existing_css(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = WebsiteBuilder(tools)
    spec = CreationSpec(kind="website", name="demo", theme="dark", color_scheme="dark")
    builder.build_website(spec)
    # Modify: make buttons bigger
    modified = builder.modify_website("demo", "increase_size", {"target": "button"})
    # Should have modified at least one file
    assert len(modified) >= 1


def test_add_page_creates_new_html(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = WebsiteBuilder(tools)
    spec = CreationSpec(kind="website", name="demo2", theme="dark", color_scheme="dark")
    builder.build_website(spec)
    modified = builder.modify_website("demo2", "add_page", {"page": "about"})
    assert any("about.html" in f for f in modified)
    assert (workspace / "demo2" / "about.html").exists()


def test_make_responsive_adds_media_query(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = WebsiteBuilder(tools)
    spec = CreationSpec(kind="website", name="responsive", theme="dark", color_scheme="dark")
    builder.build_website(spec)
    modified = builder.modify_website("responsive", "make_responsive", {})
    css = tools.read_file("responsive/styles.css")
    assert "@media" in css


# --- Project Memory ---


def test_project_memory_create_and_view(workspace: Path):
    pm = ProjectMemory(workspace)
    pm.create(name="test-project", purpose="A test project", kind="website", technologies=["HTML", "CSS"])
    view = pm.view()
    assert "test-project" in view
    assert "A test project" in view


def test_project_memory_add_change(workspace: Path):
    pm = ProjectMemory(workspace)
    pm.create(name="test", purpose="test", kind="script")
    pm.add_change("Added a new file", ["main.py"])
    data = pm._load()
    assert len(data.get("changes", [])) == 1


def test_project_memory_add_file(workspace: Path):
    pm = ProjectMemory(workspace)
    pm.create(name="test", purpose="test", kind="website")
    pm.add_file("index.html", "Main page")
    data = pm._load()
    assert len(data.get("important_files", [])) == 1


def test_project_memory_clear(workspace: Path):
    pm = ProjectMemory(workspace)
    pm.create(name="test", purpose="test", kind="website")
    assert pm.clear() is True
    assert not pm.exists()


def test_project_memory_status(workspace: Path):
    pm = ProjectMemory(workspace)
    pm.create(name="status-test", purpose="testing", kind="game")
    status = pm.status()
    assert "status-test" in status
    assert "game" in status


# --- Validators ---


def test_validator_validates_python(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    tools.write_file("test_validate.py", "print('hello')\n")
    v = Validators(tools)
    result = v.validate_file("test_validate.py")
    assert len(result.failed) == 0
    assert len(result.passed) >= 1


def test_validator_catches_python_syntax_error(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    tools.write_file("bad.py", "def broken(\n")
    v = Validators(tools)
    result = v.validate_file("bad.py")
    assert len(result.failed) == 1
    assert "SyntaxError" in result.failed[0]


def test_validator_validates_json(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    tools.write_file("data.json", '{"key": "value"}')
    v = Validators(tools)
    result = v.validate_file("data.json")
    assert len(result.failed) == 0


def test_validator_catches_bad_json(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    tools.write_file("bad.json", "{invalid json")
    v = Validators(tools)
    result = v.validate_file("bad.json")
    assert len(result.failed) == 1


def test_validator_validates_html(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    tools.write_file("page.html", "<!DOCTYPE html><html><body>Hi</body></html>")
    v = Validators(tools)
    result = v.validate_file("page.html")
    assert len(result.failed) == 0


def test_validator_validates_website_project(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = WebsiteBuilder(tools)
    spec = CreationSpec(kind="website", name="validate-me", theme="dark", color_scheme="dark")
    created = builder.build_website(spec)
    v = Validators(tools)
    result = v.validate_project(created)
    assert result.ok


# --- Guardrails ---


def test_guardrails_classify_delete_root(workspace: Path):
    tools = WorkspaceTools(workspace)
    g = Guardrails(tools)
    risk, detail = g.classify_delete(".")
    assert risk == RiskLevel.CRITICAL


def test_guardrails_classify_delete_protected_dir(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    (workspace / ".git").mkdir()
    g = Guardrails(tools)
    risk, detail = g.classify_delete(".git")
    assert risk == RiskLevel.CRITICAL


def test_guardrails_classify_delete_file(write_workspace: Path):
    tools = WorkspaceTools(write_workspace)
    g = Guardrails(tools)
    risk, detail = g.classify_delete("existing.txt")
    assert risk == RiskLevel.LOW


def test_guardrails_shell_dangerous(workspace: Path):
    tools = WorkspaceTools(workspace)
    g = Guardrails(tools)
    risk, detail = g.classify_shell("rm -rf /")
    assert risk == RiskLevel.CRITICAL


def test_guardrails_shell_safe(workspace: Path):
    tools = WorkspaceTools(workspace)
    g = Guardrails(tools)
    risk, detail = g.classify_shell("echo hello")
    assert risk == RiskLevel.SAFE


def test_guardrails_overwrite_protected(write_workspace: Path):
    tools = WorkspaceTools(write_workspace)
    (write_workspace / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    g = Guardrails(tools)
    risk, detail = g.classify_overwrite("pyproject.toml")
    assert risk == RiskLevel.HIGH


# --- File Operations ---


def test_create_dir(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    result = tools.create_dir("new_folder")
    assert "MKDIR OK" in result
    assert (write_workspace / "new_folder").is_dir()


def test_create_dir_denied_without_write(workspace: Path):
    tools = WorkspaceTools(workspace)
    result = tools.create_dir("new_folder")
    assert "WRITE DENIED" in result


def test_rename_file(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    result = tools.rename_file("existing.txt", "renamed.txt")
    assert "RENAME OK" in result
    assert (write_workspace / "renamed.txt").exists()
    assert not (write_workspace / "existing.txt").exists()


def test_delete_file_requires_confirmation(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    result = tools.delete_file("existing.txt", confirm=False)
    assert "confirmation required" in result.lower()
    assert (write_workspace / "existing.txt").exists()


def test_delete_file_with_confirmation(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    result = tools.delete_file("existing.txt", confirm=True)
    assert "DELETE OK" in result
    assert not (write_workspace / "existing.txt").exists()


def test_delete_workspace_root_blocked(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    result = tools.delete_file(".", confirm=True)
    assert "DENIED" in result


def test_delete_protected_dir_blocked(write_workspace: Path):
    (write_workspace / ".git").mkdir()
    tools = WorkspaceTools(write_workspace, allow_write=True)
    result = tools.delete_file(".git", confirm=True)
    assert "DENIED" in result


def test_edit_file_replaces_text(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    result = tools.edit_file("existing.txt", "hello", "goodbye")
    assert "EDIT OK" in result
    content = (write_workspace / "existing.txt").read_text(encoding="utf-8")
    assert "goodbye" in content
    assert "hello" not in content.replace("goodbye", "")


def test_write_files_batch(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    result = tools.write_files({
        "file1.txt": "content1",
        "file2.txt": "content2",
    })
    assert "2 ok" in result
    assert (write_workspace / "file1.txt").exists()
    assert (write_workspace / "file2.txt").exists()


# --- Agent integration ---


def test_agent_handles_creation_request(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    result = agent.run("make me a dark gaming website")
    assert "CREATION COMPLETE" in result
    assert (workspace / "dark-gaming-website" / "index.html").exists()


def test_agent_project_view_command(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    result = agent.run("project view")
    assert "PROJECT CONTEXT" in result or "dark" in result.lower()


def test_agent_project_clear(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    result = agent.run("project clear")
    assert "cleared" in result.lower()


def test_agent_payment_guidance(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("I want to sell my game")
    assert "PAYMENT GUIDANCE" in result
    assert "never" in result.lower() and "frontend" in result.lower()


def test_agent_creation_without_write_returns_plan(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("make me a website")
    assert "PLAN ONLY" in result or "plan" in result.lower()


def test_agent_existing_commands_still_work(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("who are you")
    assert "ALLINAGENT" in result


def test_agent_analyze_project_still_works(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("analyze project")
    assert "PROJECT SUMMARY" in result


# --- Local brain ---


def test_local_brain_handles_create(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("create a website")
    assert "create" in result.lower() or "ALLINAGENT" in result


def test_local_brain_handles_project(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("project view")
    assert "project" in result.lower()


def test_help_mentions_creation(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("help")
    assert "Creation" in result
    assert "make me a website" in result
    assert "project view" in result


def test_available_commands_includes_creation(workspace: Path):
    commands = LocalBrain(WorkspaceTools(workspace)).available_commands()
    assert "make me a website" in commands
    assert "project view" in commands
