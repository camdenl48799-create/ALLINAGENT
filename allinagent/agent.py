"""ALLINAGENT orchestration: local brain first, optional LLM second, creator system."""
from __future__ import annotations
from pathlib import Path
from .config import Config
from .creator import Creator
from .local_brain import LocalBrain
from .memory import LocalMemory
from .project import ProjectMemory
from .tools import WorkspaceTools


class Agent:
    def __init__(self, workspace: Path, *, dry_run=False, allow_write=False, allow_shell=False, use_llm=False, config=None, max_steps=8):
        self.workspace = workspace.resolve()
        self.tools = WorkspaceTools(self.workspace, dry_run=dry_run, allow_write=allow_write, allow_shell=allow_shell)
        self.local_brain = LocalBrain(self.tools)
        self.creator = Creator(self.tools)
        self.memory = LocalMemory(self.workspace)
        self.project = ProjectMemory(self.workspace)
        self.config = config or Config.from_env()
        self.use_llm = use_llm
        self.max_steps = max(1, max_steps)

    def run(self, prompt: str) -> str:
        if not prompt.strip():
            return "ALLINAGENT: give me a task."

        # Check for project commands first
        lower = prompt.strip().lower()

        # Project memory commands
        if lower in ("project", "project view", "project status"):
            return self.project.view() if "view" in lower else self.project.status()
        if lower == "project clear":
            if self.project.clear():
                return "Project memory cleared."
            return "Could not clear project memory."
        if lower == "project files":
            data = self.project._load()
            if not data:
                return "No project initialized."
            files = data.get("important_files", [])
            if not files:
                return "No tracked files."
            return "\n".join(f"- {f['path']}" for f in files)
        if lower == "project changes":
            data = self.project._load()
            if not data:
                return "No project initialized."
            changes = data.get("changes", [])
            if not changes:
                return "No changes recorded."
            lines = ["PROJECT CHANGES"]
            for c in changes[-10:]:
                lines.append(f"- {c.get('description', '')[:100]}")
            return "\n".join(lines)

        # Check for payment guidance requests (before creation)
        if any(w in lower for w in ("sell", "payment", "stripe", "monetize", "pricing", "subscription")):
            return self._payment_guidance(prompt)

        # Check for creation requests OR follow-up modifications
        if self.creator.can_handle(prompt):
            return self.creator.run(prompt, allow_write=self.tools.allow_write)

        # Check for follow-up modifications to existing projects
        if self.project.exists():
            is_followup, action, params = self.creator.website_builder.is_follow_up(prompt)
            if is_followup:
                return self.creator._handle_followup(action, params, prompt)

        # Existing local brain / LLM flow
        if self.local_brain.can_handle(prompt) or not self.use_llm or not self.config.has_llm:
            result = self.local_brain.run(prompt)
        else:
            try:
                from .llm import run_llm
                result = run_llm(prompt, tools=self.tools, config=self.config, max_steps=self.max_steps)
            except Exception as exc:
                result = "ALLINAGENT external model failed safely; falling back to the local brain.\nReason: " + str(exc) + "\n\n" + self.local_brain.run(prompt)
        self.memory.remember(prompt, result)
        return result

    def _payment_guidance(self, prompt: str) -> str:
        """Provide safe payment/business guidance without handling credentials."""
        return """ALLINAGENT PAYMENT GUIDANCE

ALLINAGENT can help you set up payment/selling infrastructure for your project.
Payment is entirely optional — normal users do not need any payment setup.

IMPORTANT SECURITY RULES:
  - Never put API keys, secret keys, or passwords in frontend code.
  - Store all credentials in environment variables or a .env file.
  - Never commit .env files to version control.
  - Use backend-only endpoints for payment processing.

RECOMMENDED APPROACH:
  1. Create a .env file with your payment credentials (never commit it).
  2. Create a .env.example file with placeholder values (safe to commit).
  3. Use a payment provider's SDK on the backend only.
  4. Add .env to your .gitignore.

To scaffold a .env.example file, run:
  allinagent --allow-write "create env example"

ALLINAGENT will never expose, transmit, or store your payment credentials.
All payment setup is done locally on your machine.

If you need a specific payment integration (Stripe, PayPal, etc.),
describe what you want to sell and ALLINAGENT can guide you through it."""
