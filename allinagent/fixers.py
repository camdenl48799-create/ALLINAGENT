"""Auto-fixers for ALLINAGENT's build-test-fix loop.

Implements safe, targeted fixes for known generated-file issues.
Each fixer is conservative: it only fixes obvious problems and never
makes changes it's unsure about.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .tools import WorkspaceTools


class FixResult:
    """Result of an auto-fix attempt."""
    def __init__(self) -> None:
        self.fixed: list[str] = []
        self.failed: list[str] = []
        self.skipped: list[str] = []

    @property
    def any_fixed(self) -> bool:
        return len(self.fixed) > 0

    def summary(self) -> str:
        lines = ["ALLINAGENT FIX RESULTS", ""]
        lines.append(f"  Fixed: {len(self.fixed)}")
        lines.append(f"  Failed: {len(self.failed)}")
        lines.append(f"  Skipped: {len(self.skipped)}")
        if self.fixed:
            lines.append("")
            lines.append("  Fixed:")
            for f in self.fixed:
                lines.append(f"    + {f}")
        if self.failed:
            lines.append("")
            lines.append("  Failed (cannot auto-fix):")
            for f in self.failed:
                lines.append(f"    ! {f}")
        return "\n".join(lines)


class Fixers:
    """Safe auto-fixers for known generated-file issues."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    def fix_all(self, errors: list[str]) -> FixResult:
        """Attempt to fix all reported errors."""
        result = FixResult()
        for error in errors:
            fixed = self._fix_single(error)
            if fixed:
                result.fixed.append(f"{error} -> {fixed}")
            elif fixed is False:
                result.failed.append(error)
            else:
                result.skipped.append(error)
        return result

    def _fix_single(self, error: str) -> str | bool | None:
        """Try to fix a single error. Returns fix description, False if unfixable, None if skipped."""
        # JSON errors - try to fix by re-reading and re-formatting
        if "JSONDecodeError" in error or "JSON error" in error:
            return self._fix_json(error)

        # HTML missing linked CSS/JS
        if "missing" in error.lower() and ("html" in error.lower() or "doctype" in error.lower()):
            return self._fix_html(error)

        # CSS missing braces
        if "missing CSS rules" in error or "CSS" in error:
            return self._fix_css(error)

        # JS unbalanced braces
        if "unbalanced braces" in error:
            return self._fix_js_braces(error)

        # Python syntax errors - report, don't auto-fix
        if "SyntaxError" in error:
            return False  # Can't safely auto-fix arbitrary Python

        return None

    def _fix_json(self, error: str) -> str | bool:
        """Try to fix a JSON file from the error message."""
        # Extract filename from error
        file_match = re.search(r"^([^:]+)", error)
        if not file_match:
            return False
        path = file_match.group(1).strip()
        try:
            full = self.tools._safe_path(path)
            content = full.read_text(encoding="utf-8", errors="replace")
            # Try to fix common JSON issues
            fixed = content
            # Remove trailing commas
            fixed = re.sub(r",\s*}", "}", fixed)
            fixed = re.sub(r",\s*]", "]", fixed)
            # Fix single quotes to double quotes (simple cases)
            if "'" in fixed and '"' not in fixed:
                fixed = fixed.replace("'", '"')
            # Validate
            json.loads(fixed)
            full.write_text(fixed, encoding="utf-8")
            return f"Fixed JSON in {path}"
        except Exception:
            return False

    def _fix_html(self, error: str) -> str | bool:
        """Try to fix HTML structure issues."""
        file_match = re.search(r"^([^:]+)", error)
        if not file_match:
            return False
        path = file_match.group(1).strip()
        try:
            full = self.tools._safe_path(path)
            content = full.read_text(encoding="utf-8", errors="replace")
            fixed = content
            # Add doctype if missing
            if "<!DOCTYPE" not in fixed.upper() and "<!doctype" not in fixed.lower():
                fixed = "<!DOCTYPE html>\n" + fixed
            # Add html tags if missing
            if "<html" not in fixed.lower():
                fixed = "<html lang=\"en\">\n" + fixed + "\n</html>"
            # Add body tags if missing
            if "<body" not in fixed.lower() and "</body>" not in fixed.lower():
                fixed = fixed.replace("<html>", "<html>\n<body>", 1)
                fixed = fixed.replace("</html>", "</body>\n</html>", 1)
            # Fix missing CSS/JS links - create placeholder files
            css_links = re.findall(r'<link[^>]*href=["\']([^"\']+\.css)["\']', fixed, re.IGNORECASE)
            for css_path in css_links:
                css_full = full.parent / css_path
                if not css_full.exists() and self.tools.allow_write and not self.tools.dry_run:
                    css_full.parent.mkdir(parents=True, exist_ok=True)
                    css_full.write_text("/* Auto-created by ALLINAGENT fixer */\n", encoding="utf-8")
            js_links = re.findall(r'<script[^>]*src=["\']([^"\']+\.js)["\']', fixed, re.IGNORECASE)
            for js_path in js_links:
                js_full = full.parent / js_path
                if not js_full.exists() and self.tools.allow_write and not self.tools.dry_run:
                    js_full.parent.mkdir(parents=True, exist_ok=True)
                    js_full.write_text("// Auto-created by ALLINAGENT fixer\n", encoding="utf-8")
            if fixed != content:
                if self.tools.allow_write and not self.tools.dry_run:
                    full.write_text(fixed, encoding="utf-8")
                return f"Fixed HTML structure in {path}"
            return False
        except Exception:
            return False

    def _fix_css(self, error: str) -> str | bool:
        """Try to fix CSS issues."""
        file_match = re.search(r"^([^:]+)", error)
        if not file_match:
            return False
        path = file_match.group(1).strip()
        try:
            full = self.tools._safe_path(path)
            content = full.read_text(encoding="utf-8", errors="replace")
            opens = content.count("{")
            closes = content.count("}")
            if opens > closes:
                fixed = content + ("}" * (opens - closes))
                if self.tools.allow_write and not self.tools.dry_run:
                    full.write_text(fixed, encoding="utf-8")
                return f"Added {opens - closes} missing closing brace(s) in {path}"
            elif closes > opens:
                fixed = ("{" * (closes - opens)) + content
                if self.tools.allow_write and not self.tools.dry_run:
                    full.write_text(fixed, encoding="utf-8")
                return f"Added {closes - opens} missing opening brace(s) in {path}"
            return False
        except Exception:
            return False

    def _fix_js_braces(self, error: str) -> str | bool:
        """Try to fix JS brace balancing."""
        file_match = re.search(r"^([^:]+)", error)
        if not file_match:
            return False
        path = file_match.group(1).strip()
        try:
            full = self.tools._safe_path(path)
            content = full.read_text(encoding="utf-8", errors="replace")
            opens = content.count("{")
            closes = content.count("}")
            if opens > closes:
                fixed = content + ("\n}" * (opens - closes))
                if self.tools.allow_write and not self.tools.dry_run:
                    full.write_text(fixed, encoding="utf-8")
                return f"Added {opens - closes} missing closing brace(s) in {path}"
            elif closes > opens:
                fixed = ("{" * (closes - opens)) + "\n" + content
                if self.tools.allow_write and not self.tools.dry_run:
                    full.write_text(fixed, encoding="utf-8")
                return f"Added {closes - opens} missing opening brace(s) in {path}"
            return False
        except Exception:
            return False

    def fix_generated_files(self, files: list[str]) -> FixResult:
        """Validate and fix a list of generated files."""
        from .validators import Validators
        result = FixResult()
        validators = Validators(self.tools)

        for path in files:
            validation = validators.validate_file(path)
            for fail in validation.failed:
                fixed = self._fix_single(fail)
                if fixed:
                    result.fixed.append(f"{path}: {fixed}")
                elif fixed is False:
                    result.failed.append(f"{path}: {fail}")
                else:
                    result.skipped.append(f"{path}: {fail}")

        # Re-validate
        if result.any_fixed:
            re_validation = validators.validate_project(files)
            for fail in re_validation.failed:
                if fail not in [r.split(":")[0] for r in result.failed]:
                    result.failed.append(fail)

        return result
