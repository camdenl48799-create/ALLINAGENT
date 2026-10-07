"""Checkpoint and rollback system for ALLINAGENT.

Snapshots files before major changes so users can inspect what changed
and safely undo recent operations.

Commands: checkpoint, rollback, changes, diff
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .tools import WorkspaceTools

CHECKPOINT_DIR = ".allinagent"
CHECKPOINT_FILE = "checkpoints.json"
MAX_CHECKPOINTS = 20
MAX_FILE_SNAPSHOT = 512_000  # 512KB per file


@dataclass
class FileSnapshot:
    """Snapshot of a single file at checkpoint time."""
    path: str
    existed: bool
    content: str | None = None
    size: int = 0


@dataclass
class Checkpoint:
    """A checkpoint capturing workspace state."""
    id: str
    timestamp: str
    description: str
    files: dict[str, FileSnapshot] = field(default_factory=dict)
    created_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)


class CheckpointManager:
    """Manages checkpoints for safe rollback of workspace changes."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools
        self.workspace = tools.workspace
        self.checkpoint_dir = self.workspace / CHECKPOINT_DIR
        self.path = self.checkpoint_dir / CHECKPOINT_FILE

    def create(self, description: str = "checkpoint") -> Checkpoint:
        """Create a checkpoint snapshot of all workspace files."""
        cp = Checkpoint(
            id=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            timestamp=datetime.now(timezone.utc).isoformat(),
            description=description,
        )

        for f in self.tools._iter_files():
            rel = self.tools._display(f)
            try:
                size = f.stat().st_size
                if size > MAX_FILE_SNAPSHOT:
                    cp.files[rel] = FileSnapshot(path=rel, existed=True, content=None, size=size)
                else:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    cp.files[rel] = FileSnapshot(path=rel, existed=True, content=content, size=size)
            except OSError:
                cp.files[rel] = FileSnapshot(path=rel, existed=True, content=None)

        self._save_checkpoint(cp)
        return cp

    def rollback(self, checkpoint_id: str | None = None) -> str:
        """Rollback to a checkpoint. Returns a status message."""
        checkpoints = self._load_all()
        if not checkpoints:
            return "No checkpoints available to rollback to."

        if checkpoint_id:
            cp = next((c for c in checkpoints if c["id"] == checkpoint_id), None)
            if not cp:
                return f"Checkpoint {checkpoint_id} not found."
        else:
            cp = checkpoints[-1]

        restored = 0
        removed = 0

        # Restore files that existed at checkpoint time
        for path_str, snapshot in cp.get("files", {}).items():
            try:
                full = self.tools._safe_path(path_str)
                if snapshot.get("existed"):
                    content = snapshot.get("content")
                    if content is not None:
                        full.parent.mkdir(parents=True, exist_ok=True)
                        full.write_text(content, encoding="utf-8")
                        restored += 1
                else:
                    if full.exists():
                        full.unlink()
                        removed += 1
            except Exception:
                pass

        # Remove files that exist now but weren't in the checkpoint
        cp_files = set(cp.get("files", {}).keys())
        for f in self.tools._iter_files():
            rel = self.tools._display(f)
            if rel not in cp_files:
                # This file was created after the checkpoint
                try:
                    if f.is_file():
                        f.unlink()
                        removed += 1
                    elif f.is_dir():
                        import shutil
                        shutil.rmtree(f)
                        removed += 1
                except Exception:
                    pass

        # Remove files that were explicitly tracked as created
        for path_str in cp.get("created_files", []):
            try:
                full = self.tools._safe_path(path_str)
                if full.exists():
                    if full.is_file():
                        full.unlink()
                        removed += 1
                    elif full.is_dir():
                        shutil.rmtree(full)
                        removed += 1
            except Exception:
                pass

        return f"Rolled back to checkpoint {cp.get('id', '?')}.\n  Restored {restored} files.\n  Removed {removed} files."

    def changes(self, checkpoint_id: str | None = None) -> str:
        """Show what changed since a checkpoint."""
        checkpoints = self._load_all()
        if not checkpoints:
            return "No checkpoints available."

        if checkpoint_id:
            cp = next((c for c in checkpoints if c["id"] == checkpoint_id), None)
            if not cp:
                return f"Checkpoint {checkpoint_id} not found."
        else:
            cp = checkpoints[-1]

        lines = [f"CHANGES SINCE CHECKPOINT {cp.get('id', '?')}", ""]

        # Compare current files to checkpoint
        current_files = set()
        for f in self.tools._iter_files():
            rel = self.tools._display(f)
            current_files.add(rel)

        cp_files = set(cp.get("files", {}).keys())
        created = cp.get("created_files", [])

        # New files (in current but not in checkpoint)
        new_files = current_files - cp_files
        if new_files:
            lines.append("New files:")
            for f in sorted(new_files):
                lines.append(f"  + {f}")
            lines.append("")

        # Modified files (content differs)
        modified = []
        deleted = []
        for path_str in sorted(cp_files):
            try:
                full = self.tools._safe_path(path_str)
                if not full.exists():
                    deleted.append(path_str)
                    continue
                snapshot = cp["files"].get(path_str, {})
                if snapshot.get("existed") and snapshot.get("content") is not None:
                    current = full.read_text(encoding="utf-8", errors="replace")
                    if current != snapshot.get("content", ""):
                        modified.append(path_str)
            except Exception:
                pass

        if modified:
            lines.append("Modified files:")
            for f in modified:
                lines.append(f"  ~ {f}")
            lines.append("")

        if deleted:
            lines.append("Deleted files:")
            for f in deleted:
                lines.append(f"  - {f}")
            lines.append("")

        if not new_files and not modified and not deleted:
            lines.append("No changes detected.")

        lines.append(f"Summary: {len(new_files)} new, {len(modified)} modified, {len(deleted)} deleted")
        return "\n".join(lines)

    def diff(self, path: str, checkpoint_id: str | None = None) -> str:
        """Show the diff for a specific file against a checkpoint."""
        checkpoints = self._load_all()
        if not checkpoints:
            return "No checkpoints available."

        if checkpoint_id:
            cp = next((c for c in checkpoints if c["id"] == checkpoint_id), None)
            if not cp:
                return f"Checkpoint {checkpoint_id} not found."
        else:
            cp = checkpoints[-1]

        snapshot = cp.get("files", {}).get(path)
        if not snapshot:
            return f"File {path} was not tracked in checkpoint {cp.get('id', '?')}."

        old_content = snapshot.get("content", "")
        if old_content is None:
            return f"File {path} was too large to snapshot or did not exist."

        try:
            full = self.tools._safe_path(path)
            if not full.exists():
                return f"File {path} no longer exists (was deleted after checkpoint)."
            new_content = full.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return f"Could not read file: {exc}"

        if old_content == new_content:
            return f"File {path} has not changed."

        # Simple line-by-line diff
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        lines = [f"DIFF: {path} (checkpoint {cp.get('id', '?')})", ""]

        import difflib
        diff = difflib.unified_diff(old_lines, new_lines, lineterm="", n=3)
        for line in diff:
            if line.startswith("+++") or line.startswith("---"):
                lines.append(line)
            elif line.startswith("+"):
                lines.append(f"  + {line[1:]}")
            elif line.startswith("-"):
                lines.append(f"  - {line[1:]}")
            elif line.startswith("@@"):
                lines.append(f"  {line}")
            else:
                lines.append(f"  {line}")

        return "\n".join(lines)

    def list_checkpoints(self) -> str:
        """List all available checkpoints."""
        checkpoints = self._load_all()
        if not checkpoints:
            return "No checkpoints available."

        lines = ["ALLINAGENT CHECKPOINTS", ""]
        for cp in checkpoints[-10:]:
            lines.append(f"  {cp.get('id', '?')} - {cp.get('description', '')} ({cp.get('timestamp', '')[:19]})")
        lines.append("")
        lines.append(f"Total: {len(checkpoints)} checkpoint(s)")
        lines.append("Use 'checkpoint' to create a new one.")
        lines.append("Use 'rollback' to undo to the last checkpoint.")
        lines.append("Use 'changes' to see what changed.")
        lines.append("Use 'diff <path>' to see file changes.")
        return "\n".join(lines)

    def _save_checkpoint(self, cp: Checkpoint) -> None:
        """Save a checkpoint to the checkpoint file."""
        checkpoints = self._load_all()
        cp_data = {
            "id": cp.id,
            "timestamp": cp.timestamp,
            "description": cp.description,
            "files": {path: {"existed": s.existed, "content": s.content, "size": s.size}
                      for path, s in cp.files.items()},
            "created_files": cp.created_files,
        }
        checkpoints.append(cp_data)
        checkpoints = checkpoints[-MAX_CHECKPOINTS:]
        try:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(checkpoints, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _load_all(self) -> list[dict]:
        """Load all checkpoints."""
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, ValueError, TypeError):
            return []
