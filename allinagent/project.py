"""Project metadata and context store for ALLINAGENT.

Tracks project name, purpose, technologies, important files,
user preferences, previous changes, and development state.
Stored as JSON in .allinagent/project.json within the workspace.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .memory import MEMORY_FILENAME

PROJECT_DIR = ".allinagent"
PROJECT_FILE = "project.json"
MAX_CHANGES = 200
MAX_TEXT = 8000


class ProjectMemory:
    """Persistent project context store."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.project_dir = self.workspace / PROJECT_DIR
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.project_dir / PROJECT_FILE

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save(self, data: dict) -> None:
        try:
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def exists(self) -> bool:
        return bool(self._load())

    def create(self, name: str, purpose: str, kind: str = "", technologies: list[str] | None = None) -> dict:
        """Initialize a new project context."""
        data = self._load()
        data.update({
            "name": name,
            "purpose": purpose[:MAX_TEXT],
            "kind": kind,
            "technologies": technologies or [],
            "important_files": [],
            "decisions": [],
            "changes": [],
            "state": "initialized",
            "created": datetime.now(timezone.utc).isoformat(),
            "updated": datetime.now(timezone.utc).isoformat(),
        })
        self._save(data)
        return data

    def get(self, key: str, default=None):
        return self._load().get(key, default)

    def update(self, **kwargs) -> dict:
        """Update one or more project fields."""
        data = self._load()
        for k, v in kwargs.items():
            if k in ("name", "purpose", "kind", "technologies", "important_files",
                     "decisions", "changes", "state"):
                data[k] = v
        data["updated"] = datetime.now(timezone.utc).isoformat()
        self._save(data)
        return data

    def add_change(self, description: str, files: list[str] | None = None) -> None:
        """Record a project change."""
        data = self._load()
        if not data:
            return
        changes = data.get("changes", [])
        changes.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "description": description[:MAX_TEXT],
            "files": files or [],
        })
        data["changes"] = changes[-MAX_CHANGES:]
        data["updated"] = datetime.now(timezone.utc).isoformat()
        self._save(data)

    def add_file(self, path: str, description: str = "") -> None:
        """Track an important project file."""
        data = self._load()
        if not data:
            return
        files = data.get("important_files", [])
        entry = {"path": path, "description": description}
        if entry not in files:
            files.append(entry)
            data["important_files"] = files
            self._save(data)

    def add_decision(self, decision: str) -> None:
        """Record an important project decision."""
        data = self._load()
        if not data:
            return
        decisions = data.get("decisions", [])
        decisions.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision[:MAX_TEXT],
        })
        data["decisions"] = decisions[-MAX_CHANGES:]
        self._save(data)

    def view(self) -> str:
        """Return a formatted view of project context."""
        data = self._load()
        if not data:
            return "No project context found. Use 'create <project>' to start one."

        lines = ["ALLINAGENT PROJECT CONTEXT", ""]
        lines.append(f"  Name: {data.get('name', '(unknown)')}")
        lines.append(f"  Purpose: {data.get('purpose', '(not set)')}")
        lines.append(f"  Kind: {data.get('kind', '(not set)')}")
        lines.append(f"  State: {data.get('state', '(unknown)')}")

        techs = data.get("technologies", [])
        if techs:
            lines.append(f"  Technologies: {', '.join(techs)}")

        files = data.get("important_files", [])
        if files:
            lines.append("")
            lines.append("  Important files:")
            for f in files:
                lines.append(f"    - {f['path']}" + (f" ({f.get('description', '')})" if f.get("description") else ""))

        changes = data.get("changes", [])
        if changes:
            lines.append("")
            lines.append(f"  Recent changes ({len(changes)}):")
            for c in changes[-5:]:
                lines.append(f"    - {c.get('description', '')[:100]}")

        decisions = data.get("decisions", [])
        if decisions:
            lines.append("")
            lines.append(f"  Decisions ({len(decisions)}):")
            for d in decisions[-5:]:
                lines.append(f"    - {d.get('decision', '')[:100]}")

        lines.append("")
        lines.append(f"  Location: {self.path}")
        return "\n".join(lines)

    def clear(self) -> bool:
        """Delete all project memory."""
        try:
            self.path.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def status(self) -> str:
        """Return a compact status summary."""
        data = self._load()
        if not data:
            return "ALLINAGENT PROJECT\n  No project initialized."
        return "\n".join([
            "ALLINAGENT PROJECT",
            f"  Name: {data.get('name', '(unknown)')}",
            f"  Kind: {data.get('kind', '(unknown)')}",
            f"  State: {data.get('state', '(unknown)')}",
            f"  Changes: {len(data.get('changes', []))}",
            f"  Location: {self.path}",
        ])
