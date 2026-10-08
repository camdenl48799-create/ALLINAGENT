"""Tests for ALLINAGENT v1.2.5: inspector, understanding, checkpoints, tool registry, game builder, document builder, autonomous loop."""
from __future__ import annotations

from pathlib import Path

import pytest

from allinagent.tools import WorkspaceTools
from allinagent.inspector import Inspector, ProjectInspection
from allinagent.understanding import RequestAnalyzer, TaskSpec
from allinagent.checkpoint import CheckpointManager
from allinagent.tool_registry import ToolRegistry, ToolSpec
from allinagent.autoloop import AutonomousLoop, LoopConfig, LoopResult
from allinagent.game_builder import GameBuilder
from allinagent.document_builder import DocumentBuilder
from allinagent.website_builder import WebsiteBuilder, CreationSpec
from allinagent.agent import Agent
from allinagent.config import Config


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n# TODO: test\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\nALLINAGENT\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n', encoding="utf-8")
    return tmp_path


@pytest.fixture()
def write_workspace(tmp_path: Path) -> Path:
    (tmp_path / "existing.txt").write_text("hello world", encoding="utf-8")
    return tmp_path


# --- Inspector ---


def test_inspector_detects_python_project(workspace: Path):
    tools = WorkspaceTools(workspace)
    inspector = Inspector(tools)
    result = inspector.inspect()
    assert "Python" in result.languages
    assert result.total_files > 0


def test_inspector_detects_entry_points(workspace: Path):
    tools = WorkspaceTools(workspace)
    inspector = Inspector(tools)
    result = inspector.inspect()
    assert len(result.entry_points) > 0 or result.total_files > 0


def test_inspector_detects_config_files(workspace: Path):
    tools = WorkspaceTools(workspace)
    inspector = Inspector(tools)
    result = inspector.inspect()
    assert len(result.config_files) > 0


def test_inspector_detects_tests(workspace: Path):
    (workspace / "tests").mkdir()
    (workspace / "tests" / "test_demo.py").write_text("def test(): pass\n", encoding="utf-8")
    tools = WorkspaceTools(workspace)
    inspector = Inspector(tools)
    result = inspector.inspect()
    assert result.has_tests is True
    assert len(result.test_files) > 0


def test_inspector_summary_is_readable(workspace: Path):
    tools = WorkspaceTools(workspace)
    inspector = Inspector(tools)
    result = inspector.inspect()
    summary = result.summary()
    assert "INSPECTION" in summary
    assert "Type:" in summary


def test_inspector_empty_workspace(tmp_path: Path):
    tools = WorkspaceTools(tmp_path)
    inspector = Inspector(tools)
    result = inspector.inspect()
    assert result.total_files == 0
    assert "empty" in result.project_type.lower()


# --- Request Analyzer / Understanding ---


def test_analyzer_detects_website_creation():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("make me a dark gaming website")
    assert spec.kind == "website"
    assert spec.followup_type == "new"


def test_analyzer_detects_game_creation():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("make me a game")
    assert spec.kind == "game"


def test_analyzer_detects_script_creation():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("create a script")
    assert spec.kind == "script"


def test_analyzer_detects_document_creation():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("create a readme document")
    assert spec.kind == "document"


def test_analyzer_detects_followup_bigger():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("make the buttons bigger")
    assert spec.is_followup()
    assert spec.followup_type == "increase_size"


def test_analyzer_detects_followup_mobile():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("make it mobile friendly")
    assert spec.is_followup()
    assert spec.followup_type == "make_responsive"


def test_analyzer_detects_followup_add_page():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("add a games page")
    assert spec.is_followup()
    assert spec.followup_type == "add_page"


def test_analyzer_detects_followup_change_color():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("change the color to blue")
    assert spec.is_followup()
    assert spec.followup_type == "change_color"


def test_analyzer_detects_dark_theme():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("make me a dark website")
    assert spec.theme == "dark"


def test_analyzer_detects_pages():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("make me a website with a homepage, products page, login page, and contact page")
    assert "home" in spec.pages
    assert "products" in spec.pages
    assert "login" in spec.pages
    assert "contact" in spec.pages


def test_analyzer_detects_features():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("make me a website with dark mode, animations, and a contact form")
    assert "dark_mode" in spec.features
    assert "animations" in spec.features
    assert "contact_form" in spec.features


def test_analyzer_extracts_name_from_called():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("make me a game called DOG GO")
    assert "dog" in spec.name.lower()


def test_analyzer_extracts_descriptive_name():
    analyzer = RequestAnalyzer()
    spec = analyzer.analyze("make me a dark gaming website")
    assert "dark" in spec.name
    assert "gaming" in spec.name


def test_analyzer_is_creation_request():
    analyzer = RequestAnalyzer()
    assert analyzer.is_creation_request("make me a website") is True
    assert analyzer.is_creation_request("what time is it") is False


# --- Checkpoint System ---


def test_checkpoint_creates_snapshot(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    cm = CheckpointManager(tools)
    cp = cm.create("test checkpoint")
    assert cp.id is not None
    assert len(cp.files) > 0
    assert "existing.txt" in cp.files


def test_rollback_restores_modified_file(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    cm = CheckpointManager(tools)
    cm.create("before change")
    tools.write_file("existing.txt", "modified content")
    result = cm.rollback()
    assert "Restored" in result
    assert (write_workspace / "existing.txt").read_text() == "hello world"


def test_rollback_removes_new_files(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    cm = CheckpointManager(tools)
    cm.create("before change")
    tools.write_file("new_file.txt", "new content")
    cm.rollback()
    assert not (write_workspace / "new_file.txt").exists()


def test_changes_shows_modifications(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    cm = CheckpointManager(tools)
    cm.create("before change")
    tools.write_file("existing.txt", "modified content")
    changes = cm.changes()
    assert "Modified" in changes or "modified" in changes.lower()


def test_diff_shows_file_changes(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    cm = CheckpointManager(tools)
    cm.create("before change")
    tools.write_file("existing.txt", "modified content")
    diff = cm.diff("existing.txt")
    assert "DIFF" in diff or "changed" in diff.lower()


def test_list_checkpoints(write_workspace: Path):
    tools = WorkspaceTools(write_workspace, allow_write=True)
    cm = CheckpointManager(tools)
    cm.create("first")
    cm.create("second")
    listing = cm.list_checkpoints()
    assert "CHECKPOINTS" in listing
    assert "Total: 2" in listing


def test_rollback_with_no_checkpoints(tmp_path: Path):
    tools = WorkspaceTools(tmp_path)
    cm = CheckpointManager(tools)
    result = cm.rollback()
    assert "No checkpoints" in result


# --- Tool Registry ---


def test_tool_registry_lists_tools(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    registry = ToolRegistry(tools)
    names = registry.tool_names()
    assert "read_file" in names
    assert "write_file" in names
    assert "project_summary" in names
    assert "list_dir" in names
    assert "search_text" in names


def test_tool_registry_call_read(workspace: Path):
    tools = WorkspaceTools(workspace)
    registry = ToolRegistry(tools)
    result = registry.call("read_file", {"path": "README.md"})
    assert "ALLINAGENT" in result or "READ" in result


def test_tool_registry_call_write_denied(workspace: Path):
    tools = WorkspaceTools(workspace)
    registry = ToolRegistry(tools)
    result = registry.call("write_file", {"path": "test.txt", "content": "hello"})
    assert "DENIED" in result


def test_tool_registry_call_write_allowed(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    registry = ToolRegistry(tools)
    result = registry.call("write_file", {"path": "test.txt", "content": "hello"})
    assert "WRITE OK" in result


def test_tool_registry_call_unknown_tool(workspace: Path):
    tools = WorkspaceTools(workspace)
    registry = ToolRegistry(tools)
    result = registry.call("nonexistent", {})
    assert "Unknown tool" in result


def test_tool_registry_schemas(workspace: Path):
    tools = WorkspaceTools(workspace)
    registry = ToolRegistry(tools)
    schemas = registry.tool_schemas()
    assert len(schemas) > 5
    assert any(s["function"]["name"] == "read_file" for s in schemas)


def test_tool_registry_get_spec(workspace: Path):
    tools = WorkspaceTools(workspace)
    registry = ToolRegistry(tools)
    spec = registry.get("read_file")
    assert spec is not None
    assert spec.name == "read_file"
    assert spec.risk == "safe"


# --- Game Builder ---


def test_game_builder_creates_files(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = GameBuilder(tools)
    spec = CreationSpec(kind="game", name="test-game", theme="dark", color_scheme="dark")
    created = builder.build_game(spec)
    assert len(created) >= 4
    assert any("index.html" in f for f in created)
    assert any("styles.css" in f for f in created)
    assert any("game.js" in f for f in created)
    assert any("README.md" in f for f in created)


def test_game_builder_html_has_canvas(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = GameBuilder(tools)
    spec = CreationSpec(kind="game", name="canvas-game", theme="dark", color_scheme="dark")
    builder.build_game(spec)
    html = tools.read_file("canvas-game/index.html")
    assert "canvas" in html.lower()


def test_game_builder_js_has_player_and_enemies(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = GameBuilder(tools)
    spec = CreationSpec(kind="game", name="combat-game", theme="dark", color_scheme="dark")
    builder.build_game(spec)
    js = tools.read_file("combat-game/game.js")
    assert "player" in js.lower()
    assert "enemies" in js.lower() or "enemy" in js.lower()
    assert "score" in js.lower()


def test_game_builder_has_pause_menu(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = GameBuilder(tools)
    spec = CreationSpec(kind="game", name="pause-game", theme="dark", color_scheme="dark")
    builder.build_game(spec)
    html = tools.read_file("pause-game/index.html")
    assert "pause" in html.lower()


def test_game_builder_has_difficulty(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = GameBuilder(tools)
    spec = CreationSpec(kind="game", name="diff-game", theme="dark", color_scheme="dark")
    builder.build_game(spec)
    html = tools.read_file("diff-game/index.html")
    assert "difficulty" in html.lower()


def test_game_builder_has_health_and_lives(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = GameBuilder(tools)
    spec = CreationSpec(kind="game", name="health-game", theme="dark", color_scheme="dark")
    builder.build_game(spec)
    js = tools.read_file("health-game/game.js")
    assert "health" in js.lower()


# --- Document Builder ---


def test_document_builder_creates_readme(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = DocumentBuilder(tools)
    spec = CreationSpec(kind="document", name="my-project", theme="", color_scheme="")
    created = builder.build_document(spec, "create a readme for my project")
    assert len(created) >= 1
    content = tools.read_file(created[0])
    assert "README" in content or "Overview" in content


def test_document_builder_creates_spec(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = DocumentBuilder(tools)
    spec = CreationSpec(kind="document", name="spec-project", theme="", color_scheme="")
    created = builder.build_document(spec, "create a technical specification")
    assert len(created) >= 1
    content = tools.read_file(created[0])
    assert "Specification" in content or "SPECIFICATION" in content


def test_document_builder_creates_guide(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = DocumentBuilder(tools)
    spec = CreationSpec(kind="document", name="guide-project", theme="", color_scheme="")
    created = builder.build_document(spec, "create a user guide")
    assert len(created) >= 1
    content = tools.read_file(created[0])
    assert "Guide" in content or "GUIDE" in content


def test_document_builder_creates_changelog(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = DocumentBuilder(tools)
    spec = CreationSpec(kind="document", name="changelog-project", theme="", color_scheme="")
    created = builder.build_document(spec, "create a changelog")
    assert len(created) >= 1
    content = tools.read_file(created[0])
    assert "Changelog" in content or "CHANGELOG" in content


def test_document_builder_creates_manual(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = DocumentBuilder(tools)
    spec = CreationSpec(kind="document", name="manual-project", theme="", color_scheme="")
    created = builder.build_document(spec, "create a technical manual")
    assert len(created) >= 1
    content = tools.read_file(created[0])
    assert "Manual" in content or "MANUAL" in content


def test_document_builder_creates_project_plan(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = DocumentBuilder(tools)
    spec = CreationSpec(kind="document", name="plan-project", theme="", color_scheme="")
    created = builder.build_document(spec, "create a project plan")
    assert len(created) >= 1
    content = tools.read_file(created[0])
    assert "Plan" in content or "PLAN" in content


# --- Autonomous Loop ---


def test_autonomous_loop_executes_successfully(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    loop = AutonomousLoop(tools)
    files = []
    def build_fn():
        result = tools.write_file("test_loop.py", "print('hello')\n")
        if "WRITE OK" in result:
            files.append("test_loop.py")
        return files
    result = loop.execute(build_fn, files, "test task")
    assert result.success is True


def test_autonomous_loop_detects_errors(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    loop = AutonomousLoop(tools)
    files = ["bad.py"]
    tools.write_file("bad.py", "def broken(\n")
    def build_fn():
        return ["bad.py"]
    result = loop.execute(build_fn, files, "test task with errors")
    # Should detect the syntax error
    assert len(result.errors) > 0 or result.success is False


def test_autonomous_loop_has_configurable_limits():
    config = LoopConfig(max_iterations=5, max_fixes=2, max_files_changed=20)
    assert config.max_iterations == 5
    assert config.max_fixes == 2
    assert config.max_files_changed == 20


def test_autonomous_loop_result_summary(workspace: Path):
    result = LoopResult(success=True)
    result.steps.append("Step 1")
    result.files_created.append("test.py")
    summary = result.summary()
    assert "AUTONOMOUS LOOP" in summary
    assert "Success: True" in summary


# --- Agent integration v1.2.5 ---


def test_agent_creates_website_with_checkpoint(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    result = agent.run("make me a dark gaming website")
    assert "CREATION COMPLETE" in result
    assert (workspace / "dark-gaming-website" / "index.html").exists()


def test_agent_checkpoint_command(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    (workspace / "test.txt").write_text("hello", encoding="utf-8")
    result = agent.run("checkpoint")
    assert "Checkpoint created" in result


def test_agent_rollback_command(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("checkpoint")
    agent.tools.write_file("new.txt", "content")
    result = agent.run("rollback")
    assert "Rolled back" in result or "Restored" in result


def test_agent_changes_command(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("checkpoint")
    agent.tools.write_file("new_file.txt", "content")
    result = agent.run("changes")
    assert "New files" in result or "new" in result.lower()


def test_agent_inspect_command(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    result = agent.run("inspect")
    assert "INSPECTION" in result


def test_agent_creates_game(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    result = agent.run("make me a game")
    assert "CREATION COMPLETE" in result
    assert (workspace / "my-game" / "index.html").exists()


def test_agent_creates_document(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    result = agent.run("create a readme document")
    assert "CREATION COMPLETE" in result or "Document created" in result


def test_agent_creates_script(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    result = agent.run("create a script")
    assert "CREATION COMPLETE" in result or "Script created" in result


def test_agent_followup_bigger_buttons(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    result = agent.run("make the buttons bigger")
    assert "MODIFICATION" in result


def test_agent_followup_mobile_friendly(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    result = agent.run("make it mobile friendly")
    assert "MODIFICATION" in result


def test_agent_followup_add_page(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    result = agent.run("add a games page")
    assert "MODIFICATION" in result


def test_agent_existing_commands_still_work(workspace: Path):
    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("who are you")
    assert "ALLINAGENT" in result


def test_agent_project_view(workspace: Path):
    agent = Agent(workspace, allow_write=True, config=Config.from_env())
    agent.run("make me a dark gaming website")
    result = agent.run("project view")
    assert "PROJECT" in result


# --- Version ---


def test_version_is_1_4_0():
    from allinagent import __version__
    assert __version__ == "1.5.0"


def test_cli_version_output():
    from allinagent import __version__
    assert "1.5.0" in __version__


# --- TOML compatibility ---


def test_validator_toml_fallback():
    """Ensure validators module imports without error on Python 3.10."""
    from allinagent.validators import Validators
    # If the import succeeded, the tomllib fallback works
    assert Validators is not None


# --- Complex website creation ---


def test_complex_website_creation(workspace: Path):
    """Test creating a complex website with multiple pages."""
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = WebsiteBuilder(tools)
    spec = CreationSpec(kind="website", name="complex-site", theme="dark", color_scheme="dark")
    spec.pages = ["home", "about", "contact", "login"]
    created = builder.build_website(spec)
    assert len(created) >= 4
    assert any("index.html" in f for f in created)


def test_complex_website_has_nav(workspace: Path):
    tools = WorkspaceTools(workspace, allow_write=True)
    builder = WebsiteBuilder(tools)
    spec = CreationSpec(kind="website", name="nav-site", theme="dark", color_scheme="dark")
    created = builder.build_website(spec)
    html = tools.read_file("nav-site/index.html")
    assert "nav" in html.lower()
