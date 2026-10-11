"""Project metadata and context store for ALLINAGENT.

Tracks project name, purpose, technologies, important files,
user preferences, previous changes, and development state.
Stored as JSON in .allinagent/project.json within the workspace.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ._persistence import atomic_write_json

PROJECT_DIR = ".allinagent"
PROJECT_FILE = "project.json"
MAX_CHANGES = 200
MAX_TEXT = 8000


class ProjectMemory:
    """Persistent project context store."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.project_dir = self.workspace / PROJECT_DIR
        self.path = self.project_dir / PROJECT_FILE
        self.load_error: str | None = None

    def _load(self) -> dict:
        self.load_error = None
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
            return data
        except (OSError, ValueError, TypeError) as exc:
            self.load_error = f"Could not read project metadata ({type(exc).__name__}); the original file was preserved."
            return {}

    def _save(self, data: dict) -> None:
        if self.load_error:
            raise OSError(self.load_error)
        atomic_write_json(self.path, data)

    def exists(self) -> bool:
        return bool(self._load())

    def create(self, name: str, purpose: str, kind: str = "", technologies: list[str] | None = None) -> dict:
        """Initialize a new project context."""
        data = self._load()
        if self.load_error:
            raise OSError(self.load_error)
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
        if self.load_error:
            raise OSError(self.load_error)
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
            if self.load_error:
                raise OSError(self.load_error)
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
            if self.load_error:
                raise OSError(self.load_error)
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
            if self.load_error:
                raise OSError(self.load_error)
            return
        decisions = data.get("decisions", [])
        decisions.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision[:MAX_TEXT],
        })
        data["decisions"] = decisions[-MAX_CHANGES:]
        self._save(data)

    def add_task(self, task: str, status: str = "pending") -> None:
        """Add a pending or completed task."""
        data = self._load()
        if not data:
            if self.load_error:
                raise OSError(self.load_error)
            return
        tasks = data.get("pending_tasks", [])
        tasks.append({"task": task[:MAX_TEXT], "status": status, "timestamp": datetime.now(timezone.utc).isoformat()})
        data["pending_tasks"] = tasks[-MAX_CHANGES:]
        self._save(data)

    # Compatibility aliases matching the planned API names
    def add_pending_task(self, task: str) -> None:
        """Alias for add_task with pending status."""
        self.add_task(task, status="pending")

    def add_completed_task(self, task: str) -> None:
        """Alias for add_task with completed status."""
        self.add_task(task, status="completed")

    def add_known_bug(self, description: str) -> None:
        """Alias for add_bug."""
        self.add_bug(description)

    def add_completed_feature(self, feature: str) -> None:
        """Record a completed feature in project memory."""
        data = self._load()
        if not data:
            if self.load_error:
                raise OSError(self.load_error)
            return
        features = data.get("completed_features", [])
        features.append({"feature": feature[:MAX_TEXT], "timestamp": datetime.now(timezone.utc).isoformat()})
        data["completed_features"] = features[-MAX_CHANGES:]
        self._save(data)

    def complete_task(self, task: str) -> None:
        """Mark a task as completed."""
        data = self._load()
        if not data:
            if self.load_error:
                raise OSError(self.load_error)
            return
        tasks = data.get("pending_tasks", [])
        for t in tasks:
            if task.lower() in t.get("task", "").lower():
                t["status"] = "completed"
        data["pending_tasks"] = tasks
        self._save(data)

    def add_bug(self, description: str, status: str = "open") -> None:
        """Record a known bug."""
        data = self._load()
        if not data:
            if self.load_error:
                raise OSError(self.load_error)
            return
        bugs = data.get("known_bugs", [])
        bugs.append({"description": description[:MAX_TEXT], "status": status, "timestamp": datetime.now(timezone.utc).isoformat()})
        data["known_bugs"] = bugs[-MAX_CHANGES:]
        self._save(data)

    def remember(self, note: str) -> None:
        """Store a user note/preference."""
        data = self._load()
        if not data:
            if self.load_error:
                raise OSError(self.load_error)
            return
        prefs = data.get("user_preferences", [])
        prefs.append({"note": note[:MAX_TEXT], "timestamp": datetime.now(timezone.utc).isoformat()})
        data["user_preferences"] = prefs[-MAX_CHANGES:]
        self._save(data)

    def tasks(self) -> str:
        """Show pending and completed tasks."""
        data = self._load()
        if not data:
            return f"Project metadata needs attention: {self.load_error}" if self.load_error else "No project initialized."
        tasks = data.get("pending_tasks", [])
        if not tasks:
            return "No tasks recorded."
        lines = ["PROJECT TASKS"]
        for t in tasks:
            status = t.get("status", "pending")
            mark = "[x]" if status == "completed" else "[ ]"
            lines.append(f"  {mark} {t.get('task', '')[:100]}")
        return "\n".join(lines)

    def bugs(self) -> str:
        """Show known bugs."""
        data = self._load()
        if not data:
            return f"Project metadata needs attention: {self.load_error}" if self.load_error else "No project initialized."
        bugs = data.get("known_bugs", [])
        if not bugs:
            return "No known bugs."
        lines = ["KNOWN BUGS"]
        for b in bugs:
            status = b.get("status", "open")
            mark = "!" if status == "open" else "x"
            lines.append(f"  [{mark}] {b.get('description', '')[:100]}")
        return "\n".join(lines)

    def decisions(self) -> str:
        """Show project decisions."""
        data = self._load()
        if not data:
            return f"Project metadata needs attention: {self.load_error}" if self.load_error else "No project initialized."
        decisions = data.get("decisions", [])
        if not decisions:
            return "No decisions recorded."
        lines = ["PROJECT DECISIONS"]
        for d in decisions[-10:]:
            lines.append(f"  - {d.get('decision', '')[:100]}")
        return "\n".join(lines)

    def view(self) -> str:
        """Return a formatted view of project context."""
        data = self._load()
        if not data:
            if self.load_error:
                return f"Project metadata needs attention: {self.load_error}"
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

        tasks = data.get("pending_tasks", [])
        if tasks:
            lines.append("")
            lines.append(f"  Tasks ({len(tasks)}):")
            for t in tasks:
                status = t.get("status", "pending")
                mark = "[x]" if status == "completed" else "[ ]"
                lines.append(f"    {mark} {t.get('task', '')[:100]}")

        bugs = data.get("known_bugs", [])
        if bugs:
            lines.append("")
            lines.append(f"  Known bugs ({len(bugs)}):")
            for b in bugs:
                lines.append(f"    - {b.get('description', '')[:100]}")

        lines.append("")
        lines.append(f"  Location: {self.path}")
        return "\n".join(lines)

    def clear(self) -> bool:
        """Delete all project memory."""
        try:
            atomic_write_json(self.path, {})
            self.load_error = None
            return True
        except OSError:
            return False

    def status(self) -> str:
        """Return a compact status summary."""
        data = self._load()
        if not data:
            if self.load_error:
                return f"ALLINAGENT PROJECT\n  Warning: {self.load_error}\n  Location: {self.path}"
            return "ALLINAGENT PROJECT\n  No project initialized."
        return "\n".join([
            "ALLINAGENT PROJECT",
            f"  Name: {data.get('name', '(unknown)')}",
            f"  Kind: {data.get('kind', '(unknown)')}",
            f"  State: {data.get('state', '(unknown)')}",
            f"  Changes: {len(data.get('changes', []))}",
            f"  Tasks: {len(data.get('pending_tasks', []))}",
            f"  Bugs: {len(data.get('known_bugs', []))}",
            f"  Location: {self.path}",
        ])
