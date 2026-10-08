"""Tool registry for ALLINAGENT.

Registers all tools with schemas, descriptions, and metadata.
Provides a single source of truth for tool definitions used by
both the local brain and the optional LLM tool loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .tools import WorkspaceTools
from .build import WindowsBuilder


@dataclass
class ToolSpec:
    """Specification for a single tool."""
    name: str
    description: str
    input_schema: dict
    handler: Callable
    mutates: bool = False
    requires_write: bool = False
    requires_shell: bool = False
    risk: str = "safe"  # safe, low, moderate, high, critical


class ToolRegistry:
    """Registry of all tools available to ALLINAGENT."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools
        self._registry: dict[str, ToolSpec] = {}
        self._register_all()

    def _register_all(self) -> None:
        """Register all available tools."""
        t = self.tools
        builder = WindowsBuilder(t.workspace, allow_shell=t.allow_shell, dry_run=t.dry_run)

        # Read-only tools (safe by default)
        self.register("project_summary", "Summarize workspace files and file types",
                      {"type": "object", "properties": {}}, t.project_summary)

        self.register("storage_report", "Report largest files without deleting",
                      {"type": "object", "properties": {}}, t.storage_report)

        self.register("list_dir", "List a workspace directory",
                      {"type": "object", "properties": {"path": {"type": "string"}}},
                      lambda path=".": t.list_dir(path))

        self.register("read_file", "Read a UTF-8 workspace file",
                      {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
                      lambda path: t.read_file(path))

        self.register("read_lines", "Read specific line range of a file",
                      {"type": "object", "properties": {"path": {"type": "string"},
                                                          "start": {"type": "integer"},
                                                          "end": {"type": "integer"}},
                       "required": ["path"]},
                      lambda path, start=1, end=100: t.read_lines(path, start, end))

        self.register("search_text", "Search workspace text (case-insensitive)",
                      {"type": "object", "properties": {"needle": {"type": "string"}}, "required": ["needle"]},
                      lambda needle: t.search_text(needle))

        self.register("grep", "Search workspace text with regex",
                      {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]},
                      lambda pattern: t.grep(pattern))

        self.register("tree", "Show directory tree",
                      {"type": "object", "properties": {"path": {"type": "string"},
                                                          "depth": {"type": "integer"}}},
                      lambda path=".", depth=2: t.tree(path, depth))

        self.register("extension_report", "Report file extension counts",
                      {"type": "object", "properties": {}}, t.extension_report)

        self.register("diagnostics", "Show tool diagnostics and safety state",
                      {"type": "object", "properties": {}}, t.diagnostics)

        self.register("file_exists", "Check if a file exists",
                      {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
                      lambda path: str(t.file_exists(path)))

        self.register("matching_files", "Find files matching a glob pattern",
                      {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]},
                      lambda pattern: "\n".join(t.matching_files(pattern)) or "No files found.")

        self.register("explain_path", "Explain a path's resolution and status",
                      {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
                      lambda path: t.explain_path(path))

        self.register("capability_report", "Show current capabilities and permissions",
                      {"type": "object", "properties": {}}, t.capability_report)

        self.register("safe_cleanup_note", "Show cleanup policy",
                      {"type": "object", "properties": {}}, t.safe_cleanup_note)

        # Mutation tools (require write permission)
        self.register("write_file", "Write a workspace file (requires --allow-write)",
                      {"type": "object", "properties": {"path": {"type": "string"},
                                                          "content": {"type": "string"}},
                       "required": ["path", "content"]},
                      lambda path, content: t.write_file(path, content),
                      mutates=True, requires_write=True, risk="low")

        self.register("write_files", "Write multiple files at once (requires --allow-write)",
                      {"type": "object", "properties": {"files": {"type": "object"}}, "required": ["files"]},
                      lambda files: t.write_files(files),
                      mutates=True, requires_write=True, risk="moderate")

        self.register("edit_file", "Replace text in a file (requires --allow-write)",
                      {"type": "object", "properties": {"path": {"type": "string"},
                                                          "old_str": {"type": "string"},
                                                          "new_str": {"type": "string"}},
                       "required": ["path", "old_str", "new_str"]},
                      lambda path, old_str, new_str: t.edit_file(path, old_str, new_str),
                      mutates=True, requires_write=True, risk="low")

        self.register("create_dir", "Create a directory (requires --allow-write)",
                      {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
                      lambda path: t.create_dir(path),
                      mutates=True, requires_write=True, risk="low")

        self.register("rename_file", "Rename or move a file (requires --allow-write)",
                      {"type": "object", "properties": {"old_path": {"type": "string"},
                                                          "new_path": {"type": "string"}},
                       "required": ["old_path", "new_path"]},
                      lambda old_path, new_path: t.rename_file(old_path, new_path),
                      mutates=True, requires_write=True, risk="low")

        self.register("move_file", "Move a file (requires --allow-write)",
                      {"type": "object", "properties": {"old_path": {"type": "string"},
                                                          "new_path": {"type": "string"}},
                       "required": ["old_path", "new_path"]},
                      lambda old_path, new_path: t.move_file(old_path, new_path),
                      mutates=True, requires_write=True, risk="low")

        self.register("delete_file", "Delete a file or directory (requires confirmation)",
                      {"type": "object", "properties": {"path": {"type": "string"},
                                                          "confirm": {"type": "boolean", "default": False}},
                       "required": ["path"]},
                      lambda path, confirm=False: t.delete_file(path, confirm=confirm),
                      mutates=True, requires_write=True, risk="high")

        # Shell tool (requires shell permission)
        self.register("run_shell", "Run a workspace command (requires --allow-shell)",
                      {"type": "object", "properties": {"command": {"type": "string"}},
                       "required": ["command"]},
                      lambda command: t.run_shell(command),
                      mutates=True, requires_shell=True, risk="high")

        # Build/package tools (requires shell permission)
        self.register("build_exe", "Detect a supported project, build a real Windows EXE, and show the PowerShell build log",
                      {"type": "object", "properties": {
                          "project": {"type": "string"},
                          "entry": {"type": "string"},
                          "output": {"type": "string"},
                          "timeout": {"type": "integer", "minimum": 1, "maximum": 1800}
                      }},
                      lambda project=None, entry=None, output=None, timeout=120: builder.build(project, entry, output, timeout),
                      mutates=True, requires_shell=True, risk="high")

    def register(self, name: str, description: str, input_schema: dict,
                 handler: Callable, mutates: bool = False,
                 requires_write: bool = False, requires_shell: bool = False,
                 risk: str = "safe") -> None:
        """Register a tool."""
        self._registry[name] = ToolSpec(
            name=name, description=description, input_schema=input_schema,
            handler=handler, mutates=mutates, requires_write=requires_write,
            requires_shell=requires_shell, risk=risk,
        )

    def get(self, name: str) -> ToolSpec | None:
        """Get a tool specification by name."""
        return self._registry.get(name)

    def call(self, name: str, args: dict) -> str:
        """Call a tool by name with arguments."""
        spec = self._registry.get(name)
        if not spec:
            return f"Unknown tool: {name}"

        # Check permissions
        if spec.requires_write and not self.tools.allow_write:
            return f"WRITE DENIED: {name} requires --allow-write"
        if spec.requires_write and self.tools.dry_run:
            return f"WRITE BLOCKED: {name} blocked by --dry-run"
        if spec.requires_shell and not self.tools.allow_shell:
            return f"SHELL DENIED: {name} requires --allow-shell"
        if spec.requires_shell and self.tools.dry_run:
            return f"SHELL BLOCKED: {name} blocked by --dry-run"

        try:
            return spec.handler(**args)
        except Exception as exc:
            return f"TOOL ERROR ({name}): {type(exc).__name__}: {exc}"

    def list_tools(self) -> list[ToolSpec]:
        """List all registered tools."""
        return list(self._registry.values())

    def tool_schemas(self) -> list[dict]:
        """Return OpenAI-compatible tool schemas."""
        schemas = []
        for spec in self._registry.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.input_schema,
                }
            })
        return schemas

    def tool_names(self) -> list[str]:
        """Return all tool names."""
        return list(self._registry.keys())
