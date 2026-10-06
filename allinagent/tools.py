from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

IGNORED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "bin",
    "obj",
}

MAX_READ_BYTES = 200_000
MAX_SEARCH_HITS = 40
MAX_LIST = 200


class WorkspaceTools:
    """Sandboxed tools restricted to a single workspace root."""

    def __init__(
        self,
        workspace: Path,
        *,
        dry_run: bool = False,
        allow_write: bool = False,
        allow_shell: bool = False,
    ):
        self.workspace = workspace.resolve()
        self.dry_run = dry_run
        self.allow_write = allow_write and not dry_run
        self.allow_shell = allow_shell and not dry_run

    def _safe_path(self, rel: str) -> Path:
        rel = (rel or ".").strip() or "."
        target = (self.workspace / rel).resolve()
        try:
            target.relative_to(self.workspace)
        except ValueError as e:
            raise PermissionError(f"Path escapes workspace: {rel}") from e
        return target

    def _should_skip(self, path: Path) -> bool:
        return any(part in IGNORED_DIR_NAMES for part in path.parts)

    # ---- tool implementations ------------------------------------------------

    def project_summary(self) -> str:
        files: list[Path] = []
        for p in self.workspace.rglob("*"):
            if self._should_skip(p):
                continue
            if p.is_file():
                files.append(p.relative_to(self.workspace))
        files.sort(key=lambda x: str(x).lower())
        preview = files[:80]
        lines = [
            f"Workspace: {self.workspace}",
            f"Files found (ignored common junk dirs): {len(files)}",
            "",
            "Project files:",
        ]
        lines += [f"- {p}" for p in preview]
        if len(files) > 80:
            lines.append(f"... and {len(files) - 80} more")
        return "\n".join(lines)

    def storage_report(self) -> str:
        entries: list[tuple[int, Path]] = []
        for p in self.workspace.rglob("*"):
            if not p.is_file():
                continue
            try:
                entries.append((p.stat().st_size, p.relative_to(self.workspace)))
            except OSError:
                pass
        entries.sort(reverse=True)
        lines = [
            "ALLINAGENT storage report",
            f"Workspace: {self.workspace}",
            "",
            "Largest files:",
        ]
        for size, path in entries[:25]:
            lines.append(f"- {size / 1024 / 1024:.2f} MB  {path}")
        lines += [
            "",
            "SAFE MODE: nothing was deleted.",
            "Deletion requires an explicit user request and write permission.",
        ]
        return "\n".join(lines)

    def list_dir(self, path: str = ".") -> str:
        target = self._safe_path(path)
        if not target.exists():
            return f"Not found: {path}"
        if not target.is_dir():
            return f"Not a directory: {path}"
        items: list[str] = []
        try:
            children = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError as e:
            return f"Error listing {path}: {e}"
        for child in children:
            if child.name in IGNORED_DIR_NAMES:
                continue
            rel = child.relative_to(self.workspace)
            if child.is_dir():
                items.append(f"[dir]  {rel}/")
            else:
                try:
                    sz = child.stat().st_size
                    items.append(f"[file] {rel}  ({sz} bytes)")
                except OSError:
                    items.append(f"[file] {rel}")
            if len(items) >= MAX_LIST:
                items.append("... truncated")
                break
        return "\n".join(items) if items else "(empty)"

    def read_file(self, path: str, max_chars: int = 12000) -> str:
        target = self._safe_path(path)
        if not target.exists():
            return f"Not found: {path}"
        if not target.is_file():
            return f"Not a file: {path}"
        try:
            data = target.read_bytes()
        except OSError as e:
            return f"Error reading {path}: {e}"
        if len(data) > MAX_READ_BYTES:
            data = data[:MAX_READ_BYTES]
            truncated = True
        else:
            truncated = False
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return f"Binary or non-UTF-8 file ({len(data)} bytes): {path}"
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [truncated]"
            truncated = True
        header = f"--- {path} ---"
        if truncated:
            header += " (truncated)"
        return f"{header}\n{text}"

    def write_file(self, path: str, content: str) -> str:
        if not self.allow_write:
            return (
                "WRITE DENIED: pass --allow-write (and not --dry-run) to enable. "
                f"Would have written {len(content)} chars to {path}."
            )
        target = self._safe_path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as e:
            return f"Error writing {path}: {e}"
        return f"Wrote {len(content)} chars to {path}"

    def search_text(self, pattern: str, path: str = ".", max_hits: int = MAX_SEARCH_HITS) -> str:
        root = self._safe_path(path)
        if not root.exists():
            return f"Not found: {path}"
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"Invalid regex: {e}"
        hits: list[str] = []
        paths = [root] if root.is_file() else root.rglob("*")
        for p in paths:
            if not p.is_file() or self._should_skip(p):
                continue
            try:
                if p.stat().st_size > MAX_READ_BYTES:
                    continue
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    rel = p.relative_to(self.workspace)
                    hits.append(f"{rel}:{i}: {line.strip()[:200]}")
                    if len(hits) >= max_hits:
                        hits.append("... more matches truncated")
                        return "\n".join(hits)
        return "\n".join(hits) if hits else "No matches."

    def run_shell(self, command: str, timeout: int = 30) -> str:
        if not self.allow_shell:
            return (
                "SHELL DENIED: pass --allow-shell (and not --dry-run) to enable. "
                f"Command was: {command!r}"
            )
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"Timed out after {timeout}s: {command}"
        except OSError as e:
            return f"Shell error: {e}"
        out = (proc.stdout or "") + (proc.stderr or "")
        if len(out) > 20_000:
            out = out[:20_000] + "\n... [truncated]"
        return f"exit={proc.returncode}\n{out}".rstrip()

    # ---- OpenAI tool schema + dispatch ---------------------------------------

    def openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "project_summary",
                    "description": "List project files (ignoring common junk dirs).",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "storage_report",
                    "description": "Report largest files by size. Does not delete anything.",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_dir",
                    "description": "List files and directories under a relative path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path (default '.')",
                            }
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a text file from the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative file path"},
                            "max_chars": {
                                "type": "integer",
                                "description": "Max characters to return (default 12000)",
                            },
                        },
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write text to a file (requires --allow-write).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_text",
                    "description": "Regex search across text files under a path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "Python regex"},
                            "path": {"type": "string", "description": "Relative root (default '.')"},
                        },
                        "required": ["pattern"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_shell",
                    "description": "Run a shell command in the workspace (requires --allow-shell).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "timeout": {"type": "integer", "description": "Seconds (default 30)"},
                        },
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                },
            },
        ]

    def dispatch(self, name: str, arguments: dict[str, Any] | str) -> str:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError:
                return f"Invalid JSON arguments for {name}"
        args = arguments or {}
        try:
            if name == "project_summary":
                return self.project_summary()
            if name == "storage_report":
                return self.storage_report()
            if name == "list_dir":
                return self.list_dir(str(args.get("path", ".")))
            if name == "read_file":
                mc = args.get("max_chars", 12000)
                return self.read_file(str(args["path"]), max_chars=int(mc))
            if name == "write_file":
                return self.write_file(str(args["path"]), str(args.get("content", "")))
            if name == "search_text":
                return self.search_text(str(args["pattern"]), str(args.get("path", ".")))
            if name == "run_shell":
                timeout = int(args.get("timeout", 30))
                return self.run_shell(str(args["command"]), timeout=timeout)
            return f"Unknown tool: {name}"
        except KeyError as e:
            return f"Missing argument for {name}: {e}"
        except PermissionError as e:
            return str(e)
        except Exception as e:  # noqa: BLE001 — surface tool errors to the model
            return f"Tool error ({name}): {type(e).__name__}: {e}"
