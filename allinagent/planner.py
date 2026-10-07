"""Deterministic task planning and progress tracking for ALLINAGENT."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class PlanStep:
    id: int
    title: str
    description: str
    status: str = "pending"
    result: str = ""

@dataclass
class TaskPlan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)

    @property
    def done(self) -> bool:
        return bool(self.steps) and all(s.status == "done" for s in self.steps)

class TaskPlanner:
    def plan(self, prompt: str) -> TaskPlan:
        text = prompt.strip()
        lower = text.casefold()
        steps = []
        if any(x in lower for x in ("website", "web app", "landing page", "storefront")):
            steps = [
                ("Inspect workspace", "Identify framework, entry points, package manager, and existing UI."),
                ("Plan interface", "Define pages, components, navigation, responsive behavior, and accessibility."),
                ("Build site", "Create or update frontend files without overwriting unrelated work."),
                ("Add functionality", "Wire forms, state, data flow, and optional commerce hooks."),
                ("Validate", "Run available checks and inspect the generated project for obvious issues."),
            ]
        elif any(x in lower for x in ("code", "bug", "fix", "app", "backend", "api")):
            steps = [
                ("Inspect codebase", "Map relevant files and dependencies before making changes."),
                ("Diagnose", "Identify the smallest root cause and affected interfaces."),
                ("Implement", "Apply focused changes while preserving existing behavior."),
                ("Test", "Run targeted checks and capture failures."),
                ("Polish", "Fix regressions, improve errors, and summarize final changes."),
            ]
        else:
            steps = [
                ("Understand", "Break the request into concrete requirements and constraints."),
                ("Inspect", "Check available project context and existing files."),
                ("Execute", "Perform the requested work using the safest available tools."),
                ("Verify", "Check the result and report anything that remains."),
            ]
        if any(x in lower for x in ("sell", "shop", "payment", "store")):
            steps.append(("Commerce setup", "Prepare optional selling configuration without collecting raw payment credentials."))
        return TaskPlan(text, [PlanStep(i + 1, a, b) for i, (a, b) in enumerate(steps)])

    def render(self, plan: TaskPlan) -> str:
        lines = ["ALLINAGENT PLAN", "Goal: " + plan.goal, ""]
        for s in plan.steps:
            marker = {"done":"✓","running":"→","failed":"!","pending":"○"}.get(s.status, "○")
            lines.append(f"{marker} {s.id}. {s.title} — {s.description}")
            if s.result:
                lines.append("   Result: " + s.result[:500])
        return "\n".join(lines)
