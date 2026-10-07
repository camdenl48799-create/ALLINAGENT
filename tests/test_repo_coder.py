"""Tests for repository coding workflow."""
from pathlib import Path

from allinagent.repo_coder import RepoCoder
from allinagent.tools import WorkspaceTools


def test_repo_coder_detects_repo_requests(tmp_path: Path):
    assert RepoCoder.can_handle("code this repo and add a login page")
    assert RepoCoder.can_handle("implement this project with a settings screen")


def test_repo_coder_does_not_claim_plain_question(tmp_path: Path):
    assert not RepoCoder.can_handle("what is a repository")


def test_repo_coder_parse(tmp_path: Path):
    task = RepoCoder(WorkspaceTools(tmp_path)).parse(
        'code this repo, branch feature/login, commit message "Add login", test command pytest'
    )
    assert task.branch == "feature/login"
    assert task.commit_message == "Add login"
    assert task.test_command == "pytest"


def test_repo_coder_context_reads_repo(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    coder = RepoCoder(WorkspaceTools(tmp_path))
    context = coder.context(coder.parse("code this repo and fix main.py"))
    assert "REPOSITORY CODING CONTEXT" in context
    assert "main.py" in context


def test_repo_coder_plan_is_explicit(tmp_path: Path):
    coder = RepoCoder(WorkspaceTools(tmp_path))
    plan = coder.plan(coder.parse("code this repo"))
    assert "Inspect the existing repository" in plan
    assert "Review the final diff" in plan


def test_repo_coder_coding_prompt_has_safety_rules(tmp_path: Path):
    coder = RepoCoder(WorkspaceTools(tmp_path))
    prompt = coder.coding_prompt(coder.parse("code this repo and add a feature"))
    assert "do not invent" in prompt.lower()
    assert "never expose secrets" in prompt.lower()


def test_repo_coder_status_non_repo(tmp_path: Path):
    coder = RepoCoder(WorkspaceTools(tmp_path))
    assert "Not a git repository" in coder.status_report()
