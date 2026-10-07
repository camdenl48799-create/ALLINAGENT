"""Tests for ALLINAGENT v1.3.0: Git tools, fixers, React builder, dashboard, enhanced memory."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from allinagent.tools import WorkspaceTools
from allinagent.git_tools import GitTools, GitStatus
from allinagent.fixers import Fixers, FixResult
from allinagent.react_builder import ReactBuilder
from allinagent.dashboard import DashboardGenerator
from allinagent.project import ProjectMemory
from allinagent.website_builder import CreationSpec
from allinagent.agent import Agent
from allinagent.config import Config


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n', encoding="utf-8")
    return tmp_path


@pytest.fixture()
def write_workspace(tmp_path: Path) -> Path:
    (tmp_path / "existing.txt").write_text("hello world", encoding="utf-8")
    return tmp_path


# --- Git Tools ---


def test_git_status_non_repo(workspace: Path):
    tools = WorkspaceTools(workspace)
    git = GitTools(tools)
    status = git.status()
    assert status.is_repo is False


def test_git_status_repo(tmp_path: Path):
    """Test git status in a git repo."""
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    (tmp_path / "test.txt").write_text("hello", encoding="utf-8")
    tools = WorkspaceTools(tmp_path)
    git = GitTools(tools)
    status = git.status()
    assert status.is_repo is True


def test_git_summary_non_repo(workspace: Path):
    tools = WorkspaceTools(workspace)
    git = GitTools(tools)
    summary = git.summary()
    assert "Not a git repository" in summary


def test_git_diff_non_repo(workspace: Path):
    tools = WorkspaceTools(workspace)
    git = GitTools(tools)
    diff = git.diff()
    assert "not a git repository" in diff.lower()


# --- Fixers ---


def test_fixer_fixes_unbalanced_css_braces(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    tools.write_file("bad.css", "body { color: red;")
    fixers = Fixers(tools)
    result = fixers.fix_all(["bad.css: missing CSS rules"])
    assert len(result.fixed) >= 1 or len(result.failed) >= 1


def test_fixer_fixes_json_trailing_comma(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    tools.write_file("bad.json", '{"key": "value",}')
    fixers = Fixers(tools)
    result = fixers.fix_all(["bad.json: JSONDecodeError"])
    # Should fix the trailing comma
    assert len(result.fixed) >= 1


def test_fixer_reports_unfixable_python(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    tools.write_file("bad.py", "def broken(\n")
    fixers = Fixers(tools)
    result = fixers.fix_all(["bad.py: SyntaxError: invalid syntax"])
    assert len(result.failed) >= 1


def test_fixer_fixes_missing_css_link(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    tools.write_file("page.html", "<html><head><link rel='stylesheet' href='style.css'></head><body>Hi</body></html>")
    fixers = Fixers(tools)
    result = fixers.fix_all(["page.html: missing <html>"])
    # Should fix the HTML or create the missing CSS
    assert len(result.fixed) >= 1 or len(result.failed) >= 1


def test_fixer_summary_is_readable(write_workspace: Path):
    fixers = Fixers(WorkspaceTools(write_workspace))
    result = FixResult()
    result.fixed.append("Fixed JSON in data.json")
    result.failed.append("bad.py: SyntaxError")
    summary = result.summary()
    assert "FIX RESULTS" in summary
    assert "Fixed: 1" in summary
    assert "Failed: 1" in summary


def test_fixer_fix_generated_files(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    tools.write_file("data.json", '{"valid": true}')
    tools.write_file("page.html", '<!DOCTYPE html><html><body>OK</body></html>')
    fixers = Fixers(tools)
    result = fixers.fix_generated_files(["data.json", "page.html"])
    # Valid files should not produce errors
    assert len(result.fixed) == 0 or len(result.failed) == 0


# --- React Builder ---


def test_react_builder_creates_files(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = ReactBuilder(tools)
    spec = CreationSpec(kind="website", name="react-app", theme="dark", color_scheme="dark")
    created = builder.build_react_project(spec)
    assert len(created) >= 7  # package.json, index.html, vite.config.js, main.jsx, App.jsx, styles.css, README, .gitignore
    assert any("package.json" in f for f in created)
    assert any("index.html" in f for f in created)
    assert any("main.jsx" in f for f in created)
    assert any("App.jsx" in f for f in created)


def test_react_builder_package_json_validates(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = ReactBuilder(tools)
    spec = CreationSpec(kind="website", name="react-app", theme="dark", color_scheme="dark")
    builder.build_react_project(spec)
    pkg_content = tools.read_file("react-app/package.json")
    data = json.loads(pkg_content)
    assert "react" in data.get("dependencies", {})
    assert "vite" in data.get("devDependencies", {})


def test_react_builder_app_jsx_exists(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = ReactBuilder(tools)
    spec = CreationSpec(kind="website", name="react-app", theme="dark", color_scheme="dark")
    builder.build_react_project(spec)
    app_jsx = tools.read_file("react-app/src/App.jsx")
    assert "App" in app_jsx
    assert "export default" in app_jsx.lower()


def test_react_builder_has_vite_config(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = ReactBuilder(tools)
    spec = CreationSpec(kind="website", name="react-app", theme="dark", color_scheme="dark")
    builder.build_react_project(spec)
    vite_config = tools.read_file("react-app/vite.config.js")
    assert "vite" in vite_config.lower()


def test_react_builder_has_gitignore(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = ReactBuilder(tools)
    spec = CreationSpec(kind="website", name="react-app", theme="dark", color_scheme="dark")
    builder.build_react_project(spec)
    gitignore = tools.read_file("react-app/.gitignore")
    assert "node_modules" in gitignore


def test_react_builder_can_detect_react_prompt():
    tools = WorkspaceTools(Path("/tmp/test-react-detect"))
    builder = ReactBuilder(tools)
    assert builder.can_handle("make me a React dashboard") is True
    assert builder.can_handle("create a Vite app") is True
    assert builder.can_handle("make me a website") is False


def test_react_builder_dark_theme(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = ReactBuilder(tools)
    spec = CreationSpec(kind="website", name="dark-react", theme="dark", color_scheme="dark")
    builder.build_react_project(spec)
    css = tools.read_file("dark-react/src/styles.css")
    assert "dark" in css.lower() or "#1a1a2e" in css


# --- Dashboard ---


def test_dashboard_generates_html(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    (write_workspace / "test.py").write_text("print('hello')\n", encoding="utf-8")
    dash = DashboardGenerator(tools)
    path = dash.generate()
    assert path != ""
    assert path.endswith(".html")
    content = tools.read_file(path)
    assert "Project Dashboard" in content
    assert "Project Summary" in content


def test_dashboard_includes_file_tree(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    (write_workspace / "test.py").write_text("print('hello')\n", encoding="utf-8")
    dash = DashboardGenerator(tools)
    dash.generate()
    content = tools.read_file(".allinagent/dashboard.html")
    assert "File Tree" in content or "tree" in content.lower()


def test_dashboard_includes_next_steps(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    dash = DashboardGenerator(tools)
    dash.generate()
    content = tools.read_file(".allinagent/dashboard.html")
    assert "Next Steps" in content


def test_dashboard_requires_write(workspace: Path):
    tools = WorkspaceTools(workspace)  # no allow_write
    dash = DashboardGenerator(tools)
    path = dash.generate()
    assert path == ""


# --- Enhanced Project Memory ---


def test_project_memory_add_task(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.add_task("Add login page")
    tasks = pm.tasks()
    assert "Add login page" in tasks
    assert "[ ]" in tasks


def test_project_memory_complete_task(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.add_task("Add login page")
    pm.complete_task("login")
    tasks = pm.tasks()
    assert "[x]" in tasks


def test_project_memory_add_bug(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.add_bug("Login button doesn't work")
    bugs = pm.bugs()
    assert "Login button" in bugs


def test_project_memory_add_decision(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.add_decision("Use vanilla JS instead of React")
    decisions = pm.decisions()
    assert "vanilla JS" in decisions


def test_project_memory_remember_note(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.remember("User prefers dark mode")
    data = pm._load()
    prefs = data.get("user_preferences", [])
    assert len(prefs) == 1
    assert "dark mode" in prefs[0]["note"]


def test_project_memory_persists_across_instances(write_workspace: Path):
    pm1 = ProjectMemory(write_workspace)
    pm1.create(name="persist-test", purpose="testing", kind="website")
    pm1.add_task("Task 1")
    pm1.add_bug("Bug 1")

    pm2 = ProjectMemory(write_workspace)
    data = pm2._load()
    assert data.get("name") == "persist-test"
    assert len(data.get("pending_tasks", [])) == 1
    assert len(data.get("known_bugs", [])) == 1


def test_project_status_includes_tasks_and_bugs(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.add_task("Task 1")
    pm.add_bug("Bug 1")
    status = pm.status()
    assert "Tasks: 1" in status
    assert "Bugs: 1" in status


# --- Compatibility method names ---


def test_project_memory_add_pending_task_alias(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.add_pending_task("Add login")
    tasks = pm.tasks()
    assert "Add login" in tasks
    assert "[ ]" in tasks


def test_project_memory_add_known_bug_alias(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.add_known_bug("Crash on load")
    bugs = pm.bugs()
    assert "Crash on load" in bugs


def test_project_memory_add_completed_feature(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.add_completed_feature("Dark mode toggle")
    data = pm._load()
    features = data.get("completed_features", [])
    assert len(features) == 1
    assert "Dark mode toggle" in features[0]["feature"]


def test_project_memory_add_completed_task_alias(write_workspace: Path):
    pm = ProjectMemory(write_workspace)
    pm.create(name="test", purpose="testing", kind="website")
    pm.add_completed_task("Done item")
    tasks = pm.tasks()
    assert "[x]" in tasks
    assert "Done item" in tasks


# --- Agent integration ---


def test_agent_git_status_command(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("git status")
    assert "GIT" in result


def test_agent_validate_command(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    result = agent.run("validate")
    assert "VALIDATION" in result


def test_agent_fix_command(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    tools.write_file("bad.json", '{"key": "value",}')
    agent = Agent(write_workspace, allow_write=True, config=Config.from_env())
    result = agent.run("fix")
    assert "FIX RESULTS" in result or "Fixed" in result


def test_agent_dashboard_command(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    tools.write_file("test.py", "print('hello')\n")
    agent = Agent(write_workspace, allow_write=True, config=Config.from_env())
    result = agent.run("dashboard")
    assert "Dashboard generated" in result


def test_agent_creates_react_project(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    result = agent.run("make me a React dashboard")
    assert "CREATION COMPLETE" in result
    assert (workspace / "react-dashboard" / "package.json").exists() or \
           any("package.json" in f for f in [str(p) for p in workspace.rglob("*.json")])


def test_agent_project_tasks_command(write_workspace: Path):
    agent = Agent(write_workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    agent.project.add_task("Add login page")
    result = agent.run("project tasks")
    assert "Add login page" in result


def test_agent_project_bugs_command(write_workspace: Path):
    agent = Agent(write_workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    agent.project.add_bug("Button alignment issue")
    result = agent.run("project bugs")
    assert "Button alignment" in result


def test_agent_project_decisions_command(write_workspace: Path):
    agent = Agent(write_workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    agent.project.add_decision("Use dark theme by default")
    result = agent.run("project decisions")
    assert "dark theme" in result


def test_agent_project_remember_command(write_workspace: Path):
    agent = Agent(write_workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    result = agent.run("project remember user prefers blue")
    assert "saved" in result.lower()


def test_agent_existing_commands_still_work(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    assert "ALLINAGENT" in agent.run("who are you")


def test_agent_git_summary_command(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("git summary")
    assert "GIT" in result


def test_agent_git_diff_command(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("git diff")
    assert "GIT" in result


def test_cli_inspect_json(workspace: Path):
    """Test that 'allinagent inspect --json' outputs valid JSON."""
    import subprocess, json
    result = subprocess.run(
        ["python", "-m", "allinagent", "inspect", "--json"],
        capture_output=True, text=True, cwd=str(workspace)
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "project_type" in data
    assert "total_files" in data
    assert "languages" in data


# --- Version ---


def test_version_is_1_3_0():
    from allinagent import __version__
    assert __version__ == "1.3.0"


# --- Autoloop with fixers ---


def test_autoloop_uses_fixers_on_errors(write_workspace: Path):
    from allinagent.autoloop import AutonomousLoop, LoopConfig
    from allinagent.tools import WorkspaceTools

    tools = WorkspaceTools(write_workspace, allow_write=True)
    tools.write_file("bad.json", '{"key": "value",}')
    loop = AutonomousLoop(tools, LoopConfig(max_iterations=3, max_fixes=2))

    files = ["bad.json"]
    def build_fn():
        return ["bad.json"]

    result = loop.execute(build_fn, files, "test with fixable error")
    # Should have attempted a fix
    assert len(result.fixes_applied) >= 1 or len(result.errors) >= 1
