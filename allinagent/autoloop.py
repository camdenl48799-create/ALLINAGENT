"""Autonomous build-test-fix loop for ALLINAGENT.

Implements: PLAN -> BUILD -> VALIDATE -> TEST -> DETECT ERROR -> FIX -> RETEST -> REPORT
with configurable limits to prevent infinite loops.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .tools import WorkspaceTools
from .validators import Validators
from .planner import TaskPlanner


@dataclass
class LoopConfig:
    """Configuration for the autonomous loop."""
    max_iterations: int = 10
    max_fixes: int = 3
    max_files_changed: int = 50
    max_shell_commands: int = 5
    enable_auto_fix: bool = True

    @classmethod
    def default(cls):
        return cls()


@dataclass
class LoopResult:
    """Result of an autonomous loop execution."""
    success: bool
    steps: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fixes_applied: list[str] = field(default_factory=list)
    iterations: int = 0

    def summary(self) -> str:
        lines = ["ALLINAGENT AUTONOMOUS LOOP RESULT", ""]
        lines.append(f"  Success: {self.success}")
        lines.append(f"  Iterations: {self.iterations}")
        lines.append(f"  Files created: {len(self.files_created)}")
        lines.append(f"  Files modified: {len(self.files_modified)}")
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
            for e in self.errors:
                lines.append(f"    ! {e}")
        if self.fixes_applied:
            lines.append(f"  Fixes applied: {len(self.fixes_applied)}")
            for f in self.fixes_applied:
                lines.append(f"    + {f}")
        return "\n".join(lines)


class AutonomousLoop:
    """Executes a build-test-fix loop with bounded retries."""

    def __init__(self, tools: WorkspaceTools, config: LoopConfig | None = None) -> None:
        self.tools = tools
        self.config = config or LoopConfig.default()
        self.validators = Validators(tools)
        self.planner = TaskPlanner(tools)

    def execute(self, build_fn, files_to_validate: list[str],
                description: str = "task") -> LoopResult:
        """Execute the autonomous loop.

        Args:
            build_fn: callable that performs the build/creation step
            files_to_validate: list of file paths to validate
            description: human-readable description of the task

        Returns:
            LoopResult with success/failure details
        """
        result = LoopResult(success=False)
        result.steps.append(f"Planning: {description}")

        for iteration in range(1, self.config.max_iterations + 1):
            result.iterations = iteration
            result.steps.append(f"Building (iteration {iteration})...")

            # Build step
            try:
                build_output = build_fn()
                if isinstance(build_output, list):
                    result.files_created.extend(build_output)
                elif isinstance(build_output, str) and "OK" in build_output:
                    pass
            except Exception as exc:
                result.errors.append(f"Build error: {type(exc).__name__}: {exc}")

            # Validate step
            result.steps.append("Validating files...")
            validation = self.validators.validate_project(files_to_validate)

            if validation.ok:
                result.steps.append("Validation passed.")
                result.success = True
                break

            # Error detected - attempt fix
            if not self.config.enable_auto_fix:
                for fail in validation.failed:
                    result.errors.append(fail)
                break

            if len(result.fixes_applied) >= self.config.max_fixes:
                result.steps.append(f"Max fixes ({self.config.max_fixes}) reached.")
                for fail in validation.failed:
                    result.errors.append(fail)
                break

            result.steps.append(f"Error detected. Attempting fix {len(result.fixes_applied) + 1}...")
            fixed = self._attempt_fixes(validation.failed, files_to_validate)
            result.fixes_applied.extend(fixed)

            if not fixed:
                for fail in validation.failed:
                    result.errors.append(fail)
                break

            result.steps.append("Re-validating...")

        # Final validation
        if not result.success:
            final = self.validators.validate_project(files_to_validate)
            result.success = final.ok
            if not final.ok:
                for fail in final.failed:
                    if fail not in result.errors:
                        result.errors.append(fail)

        if result.success:
            result.steps.append("Completed successfully.")
        else:
            result.steps.append("Completed with errors.")
            for err in result.errors:
                result.steps.append(f"  ERROR: {err}")

        return result

    def _attempt_fixes(self, errors: list[str], files: list[str]) -> list[str]:
        """Attempt to fix known errors. Returns list of fixes applied."""
        fixes = []

        for error in errors:
            # Python syntax errors - attempt to fix by regenerating
            if "SyntaxError" in error:
                # We can't auto-fix arbitrary Python, but we can report it
                fixes.append(f"Detected Python syntax error (cannot auto-fix): {error}")

            # JSON errors - attempt to fix
            elif "JSONDecodeError" in error:
                fixes.append(f"Detected JSON error (cannot auto-fix): {error}")

            # HTML structure errors - attempt to fix
            elif "missing <html>" in error.lower() or "missing" in error.lower():
                fixes.append(f"Detected HTML structure issue (cannot auto-fix): {error}")

            # CSS missing braces
            elif "missing CSS rules" in error:
                fixes.append(f"Detected CSS issue (cannot auto-fix): {error}")

            # JS unbalanced braces
            elif "unbalanced braces" in error:
                fixes.append(f"Detected JS brace issue (cannot auto-fix): {error}")

        return fixes[: self.config.max_fixes]

    def format_progress(self, steps: list[str]) -> str:
        """Format progress steps for user display."""
        lines = ["ALLINAGENT PROGRESS", ""]
        for i, step in enumerate(steps, 1):
            lines.append(f"  [{i}] {step}")
        return "\n".join(lines)
