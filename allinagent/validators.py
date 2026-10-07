"""Validators for generated project files.

Validates code and content without executing dangerous shell commands.
Supports Python (ast.parse), JSON, TOML, and website structure checks.
"""
from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path

from .tools import WorkspaceTools


class ValidationResult:
    """Result of a validation pass."""
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.skipped: list[str] = []

    @property
    def ok(self) -> bool:
        return len(self.failed) == 0

    def add_pass(self, file: str, detail: str = "") -> None:
        self.passed.append(f"{file}" + (f": {detail}" if detail else ""))

    def add_fail(self, file: str, detail: str) -> None:
        self.failed.append(f"{file}: {detail}")

    def add_skip(self, file: str, detail: str = "") -> None:
        self.skipped.append(f"{file}" + (f": {detail}" if detail else ""))

    def summary(self) -> str:
        lines = ["ALLINAGENT VALIDATION", ""]
        lines.append(f"  Passed: {len(self.passed)}")
        lines.append(f"  Failed: {len(self.failed)}")
        lines.append(f"  Skipped: {len(self.skipped)}")
        if self.passed:
            lines.append("")
            lines.append("  Passed files:")
            for p in self.passed:
                lines.append(f"    OK  {p}")
        if self.failed:
            lines.append("")
            lines.append("  Failed files:")
            for f in self.failed:
                lines.append(f"    FAIL  {f}")
        lines.append("")
        lines.append("  Result: " + ("ALL PASSED" if self.ok else "ERRORS FOUND"))
        return "\n".join(lines)


class Validators:
    """File validators that run without dangerous shell calls."""

    PYTHON_EXTS = {".py", ".pyi"}
    JSON_EXTS = {".json"}
    TOML_EXTS = {".toml"}
    HTML_EXTS = {".html", ".htm"}
    CSS_EXTS = {".css"}
    JS_EXTS = {".js", ".jsx", ".ts", ".tsx"}

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    def validate_file(self, path: str) -> ValidationResult:
        """Validate a single file based on its extension."""
        result = ValidationResult()
        try:
            full = self.tools._safe_path(path)
        except Exception:
            result.add_fail(path, "path escapes workspace")
            return result

        if not full.exists():
            result.add_fail(path, "file does not exist")
            return result
        if not full.is_file():
            result.add_fail(path, "not a file")
            return result

        ext = full.suffix.lower()

        if ext in self.PYTHON_EXTS:
            self._validate_python(path, full, result)
        elif ext in self.JSON_EXTS:
            self._validate_json(path, full, result)
        elif ext in self.TOML_EXTS:
            self._validate_toml(path, full, result)
        elif ext in self.HTML_EXTS:
            self._validate_html(path, full, result)
        elif ext in self.CSS_EXTS:
            self._validate_css(path, full, result)
        elif ext in self.JS_EXTS:
            self._validate_js(path, full, result)
        else:
            result.add_skip(path, "no validator for this file type")

        return result

    def _validate_python(self, path: str, full: Path, result: ValidationResult) -> None:
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
            ast.parse(content, filename=str(full))
            result.add_pass(path, "Python syntax OK")
        except SyntaxError as exc:
            result.add_fail(path, f"SyntaxError: {exc.msg} (line {exc.lineno})")
        except OSError as exc:
            result.add_fail(path, f"OSError: {exc}")

    def _validate_json(self, path: str, full: Path, result: ValidationResult) -> None:
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
            json.loads(content)
            result.add_pass(path, "JSON OK")
        except json.JSONDecodeError as exc:
            result.add_fail(path, f"JSONDecodeError: {exc}")
        except OSError as exc:
            result.add_fail(path, f"OSError: {exc}")

    def _validate_toml(self, path: str, full: Path, result: ValidationResult) -> None:
        try:
            content = full.read_bytes()
            tomllib.loads(content.decode("utf-8", errors="replace"))
            result.add_pass(path, "TOML OK")
        except Exception as exc:
            result.add_fail(path, f"TOML error: {exc}")
        except OSError as exc:
            result.add_fail(path, f"OSError: {exc}")

    def _validate_html(self, path: str, full: Path, result: ValidationResult) -> None:
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
            if "<html" in content.lower() or "<!doctype" in content.lower() or "<body" in content.lower():
                result.add_pass(path, "HTML structure OK")
            else:
                result.add_fail(path, "missing <html>, <body>, or doctype")
        except OSError as exc:
            result.add_fail(path, f"OSError: {exc}")

    def _validate_css(self, path: str, full: Path, result: ValidationResult) -> None:
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
            if "{" in content and "}" in content:
                result.add_pass(path, "CSS structure OK")
            else:
                result.add_fail(path, "missing CSS rules ({ })")
        except OSError as exc:
            result.add_fail(path, f"OSError: {exc}")

    def _validate_js(self, path: str, full: Path, result: ValidationResult) -> None:
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
            # Basic check: balanced braces
            opens = content.count("{")
            closes = content.count("}")
            if opens == closes:
                result.add_pass(path, "JS braces balanced")
            else:
                result.add_fail(path, f"unbalanced braces: {opens} open, {closes} close")
        except OSError as exc:
            result.add_fail(path, f"OSError: {exc}")

    def validate_project(self, files: list[str]) -> ValidationResult:
        """Validate a list of project files."""
        result = ValidationResult()
        for path in files:
            sub = self.validate_file(path)
            result.passed.extend(sub.passed)
            result.failed.extend(sub.failed)
            result.skipped.extend(sub.skipped)
        return result
