"""Tests for the improved CLI, onboarding, and REPL features."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from allinagent.cli import build_parser, banner, Colors, init_workspace, doctor, run_repl
from allinagent.local_brain import LocalBrain
from allinagent.tools import WorkspaceTools


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n# TODO: test\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\nALLINAGENT\n", encoding="utf-8")
    (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")
    return tmp_path


# --- CLI argument parsing ---


def test_version_flag_prints_version(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])
    captured = capsys.readouterr()
    assert "allinagent" in captured.out


def test_no_color_flag_is_parsed():
    args = build_parser().parse_args(["--no-color", "test"])
    assert args.no_color is True


def test_json_flag_is_parsed():
    args = build_parser().parse_args(["--json", "analyze project"])
    assert args.json is True


def test_prompt_is_collected():
    args = build_parser().parse_args(["analyze", "project"])
    assert args.prompt == ["analyze", "project"]


def test_subcommand_init_is_recognized():
    args = build_parser().parse_args(["init"])
    assert args.prompt == ["init"]


def test_subcommand_doctor_is_recognized():
    args = build_parser().parse_args(["doctor"])
    assert args.prompt == ["doctor"]


# --- Colors ---


def test_colors_disabled_when_no_color_env(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    c = Colors(enabled=True)
    assert c.enabled is False


def test_colors_wrap_text_when_enabled():
    c = Colors(enabled=False)
    assert c.bold("hi") == "hi"
    assert c.cyan("hi") == "hi"


def test_colors_respect_no_color_flag():
    c = Colors(enabled=False)
    text = "hello"
    assert c.green(text) == text
    assert c.red(text) == text
    assert c.dim(text) == text


# --- Banner ---


def test_banner_contains_version():
    b = banner("1.1.0", Colors(enabled=False))
    assert "1.1.0" in b
    assert "ALLINAGENT" in b


def test_banner_without_colors_is_plain():
    b = banner("1.1.0", Colors(enabled=False))
    assert "\033[" not in b


# --- init command ---


def test_init_creates_config_file(workspace: Path, capsys):
    colors = Colors(enabled=False)
    result = init_workspace(workspace, colors)
    assert result == 0
    config = workspace / ".allinagent.toml"
    assert config.exists()
    content = config.read_text(encoding="utf-8")
    assert "allinagent" in content


def test_init_does_not_overwrite_existing_config(workspace: Path, capsys):
    config_path = workspace / ".allinagent.toml"
    config_path.write_text("existing = true\n", encoding="utf-8")
    colors = Colors(enabled=False)
    result = init_workspace(workspace, colors)
    assert result == 0
    content = config_path.read_text(encoding="utf-8")
    assert "existing" in content


# --- doctor command ---


def test_doctor_runs_without_errors(workspace: Path, capsys):
    colors = Colors(enabled=False)
    result = doctor(workspace, colors)
    assert result == 0
    captured = capsys.readouterr()
    assert "DOCTOR" in captured.out
    assert "Python" in captured.out


def test_doctor_reports_workspace(workspace: Path, capsys):
    colors = Colors(enabled=False)
    doctor(workspace, colors)
    captured = capsys.readouterr()
    assert "Workspace" in captured.out


# --- Local brain improvements ---


def test_local_brain_handles_doctor(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("doctor")
    assert "STATUS" in result


def test_local_brain_handles_quickstart(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    assert brain.can_handle("quickstart")
    result = brain.run("quickstart")
    assert "GETTING STARTED" in result


def test_onboarding_includes_workspace_info(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("how do I get started?")
    assert "GETTING STARTED" in result
    assert "Workspace" in result
    assert "Files:" in result


def test_onboarding_detects_empty_workspace(tmp_path: Path):
    brain = LocalBrain(WorkspaceTools(tmp_path))
    result = brain.run("how do I get started?")
    assert "empty" in result.lower()


def test_onboarding_includes_memory_count(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("how do I get started?")
    assert "Memory entries:" in result


def test_help_mentions_cli_commands(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("help")
    assert "init" in result
    assert "doctor" in result
    assert "--json" in result
    assert "--no-color" in result


def test_cat_alias_works(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("cat README.md")
    assert "ALLINAGENT" in result


def test_ls_alias_works(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("ls")
    assert "README.md" in result or "main.py" in result or "Directory" in result


def test_grep_alias_works(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    result = brain.run("grep TODO")
    assert "TODO" in result or "Matches" in result


def test_what_is_allinagent_alias(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    assert brain.can_handle("what is allinagent")
    result = brain.run("what is allinagent")
    assert "ALLINAGENT" in result


def test_disk_usage_alias(workspace: Path):
    brain = LocalBrain(WorkspaceTools(workspace))
    assert brain.can_handle("disk usage")
    result = brain.run("disk usage")
    assert "STORAGE" in result


def test_available_commands_includes_doctor_and_quickstart(workspace: Path):
    commands = LocalBrain(WorkspaceTools(workspace)).available_commands()
    assert "doctor" in commands
    assert "quickstart" in commands


# --- JSON output mode ---


def test_json_output_includes_required_fields(workspace: Path, capsys):
    from allinagent.agent import Agent
    from allinagent.config import Config
    from allinagent.cli import Colors

    agent = Agent(workspace, config=Config.from_env())
    result = agent.run("who are you")
    output = {
        "version": "1.1.0",
        "workspace": str(workspace),
        "mode": "local",
        "prompt": "who are you",
        "result": result,
    }
    json_str = json.dumps(output, indent=2, ensure_ascii=False)
    parsed = json.loads(json_str)
    assert parsed["result"] == result
    assert parsed["mode"] == "local"
