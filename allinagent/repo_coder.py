"""Repository coding workflow for ALLINAGENT."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .git_tools import GitTools
from .inspector import Inspector
from .tools import WorkspaceTools


@dataclass(frozen=True)
class RepoTask:
    request: str
    branch: str | None = None
    commit_message: str | None = None
    test_command: str | None = None


class RepoCoder:
    """Prepare an inspect-first workflow for coding an existing repository."""

    MARKERS = (
        "code this repo", "code the repo", "modify the repo", "update the repo",
        "implement in the repo", "fix the repo", "work on this repo",
        "make code for this repo", "make code for the repo",
        "implement this project", "fix this project", "add this feature to the repo",
    )

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools
        self.git = GitTools(tools)
        self.inspector = Inspector(tools)

    @classmethod
    def can_handle(cls, prompt: str) -> bool:
        text = " ".join(prompt.lower().split())
        words = ("code", "fix", "implement", "update", "modify", "change")
        return any(marker in text for marker in cls.MARKERS) or (
            ("repo" in text or "repository" in text)
            and any(word in text for word in words)
        )

    def parse(self, prompt: str) -> RepoTask:
        text = " ".join(prompt.strip().split())
        branch = None
        commit = None
        test = None
        match = re.search(r"(?:branch|on branch)\s+([A-Za-z0-9._/-]+)", text, re.I)
        if match:
            branch = match.group(1)
        match = re.search(r'(?:commit message|commit as)\s*[:=]?\s*["\']([^"\']+)["\']', text, re.I)
        if match:
            commit = match.group(1)
        match = re.search(r'(?:run tests with|test command)\s*[:=]?\s+([^,]+)', text, re.I)
        if match:
            test = match.group(1).strip()
        return RepoTask(text, branch, commit, test)

    def context(self, task: RepoTask) -> str:
        inspection = self.inspector.inspect()
        status = self.git.status()
        lines = [
            "ALLINAGENT REPOSITORY CODING CONTEXT", "",
            f"Workspace: {self.tools.workspace}",
            f"Repository: {'yes' if status.is_repo else 'no'}",
            f"Branch: {status.branch or '(none)'}",
            f"Project type: {inspection.project_type}",
            f"Languages: {', '.join(inspection.languages) or '(unknown)'}",
            f"Frameworks: {', '.join(inspection.frameworks) or '(none detected)'}",
            f"Entry points: {', '.join(inspection.entry_points[:10]) or '(none detected)'}",
            f"Tests: {', '.join(inspection.test_files[:10]) or '(none detected)'}", "",
            "Request:", task.request, "", "Changed files:",
        ]
        lines.extend(f"- {p}" for p in (status.changed + status.staged + status.untracked)[:30])
        return "\n".join(lines)

    def plan(self, task: RepoTask) -> str:
        status = self.git.status()
        inspection = self.inspector.inspect()
        lines = [
            "ALLINAGENT REPO CODING PLAN", "",
            "1. Inspect the existing repository and relevant files.",
            "2. Identify the smallest safe set of files to change.",
            "3. Preserve existing architecture and public APIs unless required otherwise.",
            "4. Implement the requested feature or fix.",
            "5. Validate changed files and run project tests when execution is permitted.",
            "6. Review the final diff and report every changed file.",
        ]
        if task.branch:
            lines.append(f"7. Use branch: {task.branch}")
        if task.commit_message:
            lines.append(f"8. Optional local commit message: {task.commit_message}")
        if not status.is_repo:
            lines += ["", "WARNING: workspace is not a Git repository."]
        if not inspection.total_files:
            lines += ["", "WARNING: repository appears empty."]
        return "\n".join(lines)

    def coding_prompt(self, task: RepoTask) -> str:
        return f"""You are coding inside an existing repository with ALLINAGENT.

TASK:
{task.request}

RULES:
- Inspect the repository before editing.
- Read relevant existing files; never invent their contents.
- Make the smallest coherent implementation.
- Preserve existing conventions and APIs unless a breaking change is requested.
- Use workspace tools to create/edit files.
- Do not delete unrelated files.
- Never expose secrets, tokens, private keys, or .env contents.
- Validate changed code after editing.
- Run relevant tests when shell permission is available.
- Review the final diff and report exactly what changed.
- If the task cannot be completed safely, stop and explain why.

REPOSITORY CONTEXT:
{self.context(task)}
"""

    def status_report(self) -> str:
        return self.git.status().summary()
