"""Persistent, local-only memory for ALLINAGENT."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ._persistence import atomic_write_json

MEMORY_FILENAME = ".allinagent-memory.json"
MAX_ENTRIES = 1000
MAX_TEXT = 12000


class LocalMemory:
    """Small persistent conversation/project memory store."""
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.path = self.workspace / MEMORY_FILENAME
        self.load_error: str | None = None

    def _load(self) -> list[dict[str, str]]:
        self.load_error = None
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            self.load_error = f"Could not read saved memory ({type(exc).__name__})."
            return []
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            self.load_error = "Saved memory has an invalid format; the original file was preserved."
            return []
        return data[-MAX_ENTRIES:]

    def _save(self, entries: list[dict[str, str]]) -> None:
        atomic_write_json(self.path, entries[-MAX_ENTRIES:])

    def remember(self, prompt: str, response: str) -> None:
        entries = self._load()
        if self.load_error:
            raise OSError(self.load_error)
        entries.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt[:MAX_TEXT],
            "response": response[:MAX_TEXT],
        })
        self._save(entries)

    def recent(self, limit: int = 10) -> list[dict[str, str]]:
        entries = self._load()
        return entries[-max(1, min(limit, 50)):]

    def clear(self) -> bool:
        try:
            # Keep the legacy API but make the empty state explicit in JSON.
            atomic_write_json(self.path, [])
            self.load_error = None
            return True
        except OSError:
            return False

    def status(self) -> str:
        entries = self._load()
        lines = [
            "ALLINAGENT MEMORY",
            f"- location: {self.path}",
            f"- entries: {len(entries)}",
            "- storage: local workspace",
            "- network sync: disabled",
        ]
        if self.load_error:
            lines.append(f"- warning: {self.load_error}")
        return "\n".join(lines)

    def context(self, limit: int = 8) -> str:
        entries = self.recent(limit)
        if self.load_error:
            return f"Saved local memory needs attention: {self.load_error}"
        if not entries:
            return "No saved local memory."
        lines = ["RECENT LOCAL MEMORY"]
        for item in entries:
            lines.extend([f"User: {item.get('prompt', '')}", f"ALLINAGENT: {item.get('response', '')}", ""])
        return "\n".join(lines).strip()
