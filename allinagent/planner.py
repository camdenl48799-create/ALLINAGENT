"""Task planning for ALLINAGENT's creation workflow.

Produces user-facing progress summaries (PLAN -> MODIFY -> VALIDATE -> REPORT)
without exposing any hidden chain-of-thought reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .tools import WorkspaceTools


@dataclass(frozen=True)
class PlanStep:
    """A single step in a task plan."""
    label: str
    summary: str
    action: Callable[[], str] | None = None


@dataclass
class TaskResult:
    """Result of executing a task plan."""
    success: bool
    summary: str
    steps: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class TaskPlanner:
    """Builds deterministic, side-effect-aware task plans for creation requests."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    def plan_creation(self, kind: str, name: str, theme: str = "", features: list[str] | None = None) -> list[PlanStep]:
        """Build a plan for a creation task.

        Returns steps with user-facing summaries only.
        """
        features = features or []
        steps: list[PlanStep] = []

        steps.append(PlanStep(
            label="Create project structure",
            summary="Creating project structure...",
            action=None,
        ))

        if kind == "website":
            steps.append(PlanStep(
                label="Write website files",
                summary="Writing website files...",
                action=None,
            ))
            steps.append(PlanStep(
                label="Add styling and assets",
                summary=f"Adding {theme or 'default'} theme styling...",
                action=None,
            ))
            if features:
                steps.append(PlanStep(
                    label="Add requested features",
                    summary="Adding requested features...",
                    action=None,
                ))
        elif kind == "game":
            steps.append(PlanStep(
                label="Write game files",
                summary="Writing game files...",
                action=None,
            ))
            steps.append(PlanStep(
                label="Add gameplay logic",
                summary="Writing gameplay system...",
                action=None,
            ))
            steps.append(PlanStep(
                label="Add UI",
                summary="Adding game UI...",
                action=None,
            ))
        elif kind == "script":
            steps.append(PlanStep(
                label="Write script",
                summary="Writing script code...",
                action=None,
            ))
        elif kind == "document":
            steps.append(PlanStep(
                label="Write document",
                summary="Writing document content...",
                action=None,
            ))
        else:
            steps.append(PlanStep(
                label="Write project files",
                summary="Writing project files...",
                action=None,
            ))

        steps.append(PlanStep(
            label="Validate files",
            summary="Checking for errors...",
            action=None,
        ))
        steps.append(PlanStep(
            label="Report results",
            summary="Finishing up...",
            action=None,
        ))
        return steps

    def execute_plan(self, steps: list[PlanStep]) -> TaskResult:
        """Execute a plan and return results."""
        result = TaskResult(success=True, summary="")
        for step in steps:
            result.steps.append(step.summary)
            if step.action:
                try:
                    output = step.action()
                    if output:
                        result.steps.append(output)
                except Exception as exc:
                    result.errors.append(f"{step.label}: {type(exc).__name__}: {exc}")
                    result.success = False
        if result.success:
            result.summary = "Task completed successfully."
        else:
            result.summary = f"Task completed with {len(result.errors)} error(s)."
        return result

    def format_progress(self, steps: list[PlanStep]) -> list[str]:
        """Return user-facing progress messages only."""
        return [s.summary for s in steps]
