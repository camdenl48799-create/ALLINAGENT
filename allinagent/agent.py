"""ALLINAGENT 1.1.0 orchestration: memory, planning, projects, web building and optional LLM."""
from __future__ import annotations
from pathlib import Path
from .config import Config
from .local_brain import LocalBrain
from .memory import LocalMemory
from .tools import WorkspaceTools
from .projects import ProjectStore
from .planner import TaskPlanner
from .web_builder import WebBuilder
from .commerce import CommerceManager

class Agent:
    def __init__(self, workspace: Path, *, dry_run=False, allow_write=False, allow_shell=False, use_llm=False, config=None, max_steps=8):
        self.workspace = workspace.resolve()
        self.tools = WorkspaceTools(self.workspace, dry_run=dry_run, allow_write=allow_write, allow_shell=allow_shell)
        self.local_brain = LocalBrain(self.tools)
        self.memory = LocalMemory(self.workspace)
        self.projects = ProjectStore(self.workspace)
        self.config = config or Config.from_env()
        self.use_llm = use_llm
        self.max_steps = max(1, max_steps)
        self.planner = TaskPlanner()
        self.web = WebBuilder(self.tools)

    def plan(self, prompt: str) -> str:
        return self.planner.render(self.planner.plan(prompt))

    def run(self, prompt: str) -> str:
        if not prompt.strip():
            return "ALLINAGENT: give me a task."
        lower = prompt.casefold()
        if lower in {"projects", "project list", "list projects"}:
            result = self.projects.summary()
        elif lower.startswith("plan "):
            result = self.plan(prompt[5:])
        elif lower in {"selling", "selling status", "commerce", "payment status"}:
            result = CommerceManager(self.workspace).status()
        elif "create website" in lower or "build website" in lower:
            title = prompt.split(":", 1)[-1].strip() or "ALLINAGENT Website"
            result = self.web.scaffold(title)
        elif self.local_brain.can_handle(prompt) or not self.use_llm or not self.config.has_llm:
            result = self.local_brain.run(prompt)
        else:
            try:
                from .llm import run_llm
                result = run_llm(prompt, tools=self.tools, config=self.config, max_steps=self.max_steps)
            except Exception as exc:
                result = "ALLINAGENT external model failed safely; falling back to the local brain.\nReason: " + str(exc) + "\n\n" + self.local_brain.run(prompt)
        self.memory.remember(prompt, result)
        return result
