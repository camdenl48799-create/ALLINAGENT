"""Persistent, local-only memory for ALLINAGENT.

Memory is stored inside the configured workspace so it can be inspected,
backed up, or deleted by the user. It is intentionally plain JSON.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

MEMORY_FILENAME = ".allinagent-memory.json"
MAX_ENTRIES = 1000
MAX_TEXT = 12000

class LocalMemory:
    """Small persistent conversation/project memory store."""
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.path = self.workspace / MEMORY_FILENAME

    def _load(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        return data if isinstance(data, list) else []

    def _save(self, entries: list[dict[str, str]]) -> None:
        self.path.write_text(json.dumps(entries[-MAX_ENTRIES:], ensure_ascii=False, indent=2), encoding="utf-8")

    def remember(self, prompt: str, response: str) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt[:MAX_TEXT],
            "response": response[:MAX_TEXT],
        }
        entries = self._load()
        entries.append(entry)
        try:
            self._save(entries)
        except OSError:
            pass

    def recent(self, limit: int = 10) -> list[dict[str, str]]:
        return self._load()[-max(1, min(limit, 50)):]

    def clear(self) -> bool:
        try:
            self.path.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def status(self) -> str:
        return "\n".join([
            "ALLINAGENT MEMORY",
            f"- location: {self.path}",
            f"- entries: {len(self._load())}",
            "- storage: local workspace",
            "- network sync: disabled",
        ])

    def context(self, limit: int = 8) -> str:
        entries = self.recent(limit)
        if not entries:
            return "No saved local memory."
        lines = ["RECENT LOCAL MEMORY"]
        for item in entries:
            lines.extend([f"User: {item.get('prompt', '')}", f"ALLINAGENT: {item.get('response', '')}", ""])
        return "\n".join(lines).strip()
