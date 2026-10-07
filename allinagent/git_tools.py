"""Git integration tools for ALLINAGENT.

Provides safe, read-only git operations for project inspection and status.
No auto-push or destructive git operations without explicit user action.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .tools import WorkspaceTools


@dataclass
class GitStatus:
    """Result of a git status check."""
    is_repo: bool = False
    branch: str = ""
    changed: list[str] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    recent_commits: list[dict] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0

    def summary(self) -> str:
        if not self.is_repo:
            return "ALLINAGENT GIT\n  Not a git repository."
        lines = ["ALLINAGENT GIT STATUS", ""]
        lines.append(f"  Branch: {self.branch}")
        if self.ahead or self.behind:
            lines.append(f"  Ahead: {self.ahead}, Behind: {self.behind}")
        lines.append(f"  Changed: {len(self.changed)}")
        lines.append(f"  Staged: {len(self.staged)}")
        lines.append(f"  Untracked: {len(self.untracked)}")
        if self.changed:
            lines.append("")
            lines.append("  Changed files:")
            for f in self.changed[:20]:
                lines.append(f"    ~ {f}")
        if self.staged:
            lines.append("")
            lines.append("  Staged files:")
            for f in self.staged[:20]:
                lines.append(f"    + {f}")
        if self.untracked:
            lines.append("")
            lines.append("  Untracked files:")
            for f in self.untracked[:20]:
                lines.append(f"    ? {f}")
        if self.recent_commits:
            lines.append("")
            lines.append("  Recent commits:")
            for c in self.recent_commits[:10]:
                lines.append(f"    {c.get('hash', '?')[:8]} {c.get('message', '')[:80]}")
        return "\n".join(lines)


class GitTools:
    """Safe git operations for project inspection."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools
        self.workspace = tools.workspace

    def _run_git(self, *args: str) -> str:
        """Run a git command safely."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            return ""

    def status(self) -> GitStatus:
        """Get the git status of the workspace."""
        result = GitStatus()

        if not (self.workspace / ".git").is_dir():
            return result

        result.is_repo = True

        # Branch
        result.branch = self._run_git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"

        # Status porcelain
        status_output = self._run_git("status", "--porcelain")
        if status_output:
            for line in status_output.splitlines():
                if len(line) < 3:
                    continue
                code = line[:2]
                path = line[3:].strip().strip('"')
                if code.startswith("??"):
                    result.untracked.append(path)
                elif code.startswith("A") or code.startswith("M") and not code[1].isspace():
                    result.staged.append(path)
                else:
                    result.changed.append(path)

        # Recent commits
        log_output = self._run_git("log", "--oneline", "-10")
        if log_output:
            for line in log_output.splitlines():
                parts = line.split(" ", 1)
                result.recent_commits.append({
                    "hash": parts[0] if parts else "",
                    "message": parts[1] if len(parts) > 1 else "",
                })

        # Ahead/behind
        ahead_behind = self._run_git("rev-list", "--left-right", "--count", "HEAD...@{upstream}")
        if ahead_behind and "\t" in ahead_behind:
            try:
                parts = ahead_behind.split("\t")
                result.ahead = int(parts[0])
                result.behind = int(parts[1]) if len(parts) > 1 else 0
            except ValueError:
                pass

        return result

    def diff(self, path: str | None = None) -> str:
        """Get a git diff for the workspace or a specific file."""
        if not (self.workspace / ".git").is_dir():
            return "GIT: not a git repository."

        args = ["diff"]
        if path:
            args.append("--")
            args.append(path)
        diff_output = self._run_git(*args)
        if not diff_output:
            return "GIT: no changes to diff."
        return f"ALLINAGENT GIT DIFF\n\n{diff_output}"

    def summary(self) -> str:
        """Get a compact git summary."""
        s = self.status()
        if not s.is_repo:
            return "ALLINAGENT GIT SUMMARY\n  Not a git repository."
        lines = ["ALLINAGENT GIT SUMMARY", ""]
        lines.append(f"  Branch: {s.branch}")
        lines.append(f"  Total changes: {len(s.changed) + len(s.staged) + len(s.untracked)}")
        lines.append(f"  Recent commits: {len(s.recent_commits)}")
        return "\n".join(lines)

    def can_commit(self) -> bool:
        """Check if there are staged changes ready to commit."""
        s = self.status()
        return s.is_repo and len(s.staged) > 0

    def safe_commit(self, message: str) -> str:
        """Create a local git commit. Does NOT push."""
        if not (self.workspace / ".git").is_dir():
            return "GIT: not a git repository."
        if not self.tools.allow_shell:
            return "GIT DENIED: git operations require --allow-shell."
        if self.tools.dry_run:
            return "GIT BLOCKED: --dry-run is active."
        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return f"GIT COMMIT OK\n  {result.stdout.strip()}"
            return f"GIT COMMIT FAILED\n  {result.stderr.strip() or result.stdout.strip()}"
        except (subprocess.TimeoutExpired, OSError) as exc:
            return f"GIT ERROR: {type(exc).__name__}: {exc}"
