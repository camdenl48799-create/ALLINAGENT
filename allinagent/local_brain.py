"""Polished deterministic local brain for ALLINAGENT.

This module is deliberately not presented as a foundation model. It is an
offline intent engine that recognizes useful coding-agent requests, builds
small deterministic plans, invokes local tools, and reports what happened.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .tools import WorkspaceTools
from .creator import Creator

IDENTITY = (
    "I'm ALLINAGENT — an independent, local-first AI coding agent. "
    "My local brain and tools run on your machine. External models are optional fuel. "
    "I can help you create websites, games, scripts, and other projects."
)


@dataclass(frozen=True)
class Intent:
    name: str
    confidence: int
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanStep:
    label: str
    action: Callable[[], str]


class LocalBrain:
    """Deterministic offline intent router and planner."""

    MAX_OUTPUT = 30_000

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools
        self._patterns: list[tuple[str, tuple[str, ...], int]] = [
            ("identity", (r"\bwho are you\b", r"\bwhat are you\b", r"\bwhat is allinagent\b"), 100),
            ("help", (r"^help$", r"\bwhat can you do\b", r"\bcommands\b", r"^what commands\b"), 95),
            ("onboarding", (
                r"^what do i do\??$",
                r"^how do i (get )?started\??$",
                r"^how do i set (this|it) up\??$",
                r"^how do i use (this|it)\??$",
                r"^how does this work\??$",
                r"\bgetting started\b",
                r"\bsetup (help|guide)\b",
                r"\bquickstart\b",
            ), 98),
            ("capabilities", (r"\bcapabilit(?:y|ies)\b", r"\bpermissions\b", r"\bsafety\b"), 90),
            ("summary", (
                r"\banaly[sz]e\b.*\b(project|repo|repository|code)\b",
                r"\bproject (summary|structure)\b",
                r"\bworkspace (summary|structure)\b",
            ), 90),
            ("storage", (r"\bfree (up )?space\b", r"\bstorage\b", r"\blargest files?\b", r"\bdisk usage\b"), 90),
            ("list", (
                r"^list( files| directory| folder)?\b",
                r"\bshow (me )?(files|directory|folder)\b",
                r"^ls\b",
                r"^dir\b",
            ), 85),
            ("read", (
                r"^read\b",
                r"^cat\b",
                r"\bshow (me )?the file\b",
                r"\bopen (the )?file\b",
            ), 85),
            ("search", (
                r"^(find|search)\b",
                r"\bsearch (the )?workspace\b",
                r"^grep\b",
            ), 85),
            ("status", (
                r"\bstatus\b.*\b(project|workspace|repo)\b",
                r"\bworkspace status\b",
                r"^doctor\b",
            ), 80),
            ("plan", (
                r"\bplan\b",
                r"\bwhat should i do\b",
                r"\bnext steps\b",
                r"\bworkflow\b",
            ), 75),
            ("create", (
                r"\bmake me\b",
                r"\bcreate\b",
                r"\bbuild me\b",
                r"\bgenerate\b",
                r"\bscaffold\b",
                r"\blet'?s make\b",
                r"\bi want\b.*\b(?:website|game|app|script|tool)\b",
            ), 70),
            ("project", (
                r"\bproject\b",
                r"\bproject (view|status|clear|files|changes|tasks|bugs|decisions|remember)\b",
            ), 72),
        ]

    def can_handle(self, prompt: str) -> bool:
        return self._classify(prompt).confidence >= 70

    def _classify(self, prompt: str) -> Intent:
        text = " ".join(prompt.strip().split())
        if not text:
            return Intent("empty", 0)

        matches: list[Intent] = []
        for name, patterns, confidence in self._patterns:
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                matches.append(Intent(name, confidence))

        if not matches:
            return Intent("unknown", 0)

        matches.sort(key=lambda item: item.confidence, reverse=True)
        winner = matches[0]
        return Intent(winner.name, winner.confidence, self._extract_args(winner.name, text))

    def _extract_args(self, name: str, text: str) -> tuple[str, ...]:
        if name == "read":
            match = re.search(
                r"""(?:read|open|show(?: me)?(?: the)?|cat)\s+(?:file\s+)?['\"]?(.+?)['\"]?$""",
                text,
                re.IGNORECASE,
            )
            return (match.group(1).strip(),) if match else ()

        if name == "list":
            match = re.search(
                r"^(?:list(?: files| directory| folder)?|ls|dir)\s*(.*)$",
                text,
                re.IGNORECASE,
            )
            value = (match.group(1) or ".").strip()
            return (value or ".",)

        if name == "search":
            match = re.search(
                r"""^(?:find|search|grep)(?: for)?\s+['\"]?(.+?)['\"]?$""",
                text,
                re.IGNORECASE,
            )
            return (match.group(1).strip(),) if match else ()

        return ()

    def run(self, prompt: str) -> str:
        intent = self._classify(prompt)
        handlers = {
            "identity": self._identity,
            "help": self._help,
            "onboarding": self._onboarding,
            "capabilities": self._capabilities,
            "summary": self._summary,
            "storage": self._storage,
            "list": lambda: self._list(intent),
            "read": lambda: self._read(intent),
            "search": lambda: self._search(intent),
            "status": self._status,
            "plan": self._plan,
            "create": self._create_hint,
            "project": self._project_hint,
            "empty": lambda: "ALLINAGENT: give me a task.",
            "unknown": self._unknown,
        }
        return self._limit_output(handlers[intent.name]())

    def _identity(self) -> str:
        return IDENTITY

    def _help(self) -> str:
        return """ALLINAGENT LOCAL MODE

Identity
  who are you              Explain ALLINAGENT's identity.

Creation
  make me a website        Create a website project.
  make me a game           Create a game project.
  make me a React app      Create a React/Vite project.
  create a script           Create a Python script.
  build me a document       Create a document.

Project
  project view              Show project context and memory.
  project status            Quick project status.
  project files             List tracked files.
  project changes           Show recent changes.
  project tasks             Show pending and completed tasks.
  project bugs              Show known bugs.
  project decisions         Show project decisions.
  project remember <note>  Save a note to project memory.
  project clear             Delete project memory.

Inspection & Validation
  inspect                   Inspect the project structure.
  validate                  Validate all project files.
  fix                       Attempt to fix validation errors.
  dashboard                 Generate a project dashboard (HTML).

Git
  git status                Show git status.
  git diff                  Show git diff.
  git summary               Compact git summary.

Checkpoint
  checkpoint                Create a snapshot.
  rollback                  Undo to last checkpoint.
  changes                   See what changed since checkpoint.
  diff <path>               Show file diff against checkpoint.

Workspace
  analyze project          Summarize files and file types.
  list files               List the workspace root.
  list files <path>        List a workspace directory.
  read file <path>         Read a UTF-8 text file.
  find <text>              Search text across the workspace.
  free up space            Report largest files without deleting.
  status project           Show local capability/status information.

Planning
  plan                     Explain the safe local workflow.

Safety
  Reads are available by default.
  Writes require --allow-write.
  Shell execution requires --allow-shell.
  --dry-run disables mutations even when permissions are supplied.
  Paths are sandboxed to the configured workspace.
  File deletion requires explicit confirmation.

CLI commands
  allinagent init           Scaffold a workspace config (.allinagent.toml).
  allinagent doctor         Run diagnostics and health checks.
  allinagent --version       Show the installed version.
  allinagent --json <task>   Output results as JSON.
  allinagent --no-color      Disable colored output.
  allinagent inspect --json  Output project inspection as JSON.

For broader reasoning, explicitly opt into an OpenAI-compatible model with --llm."""

    def _onboarding(self) -> str:
        from .memory import LocalMemory

        file_count = sum(1 for _ in self.tools._iter_files())
        mem = LocalMemory(self.tools.workspace)
        mem_count = len(mem._load())

        intro = """ALLINAGENT GETTING STARTED

Welcome to ALLINAGENT — an independent, local-first AI coding agent.
No API key is required. Your code and prompts stay on your machine."""

        workspace_info = f"""
Workspace
  {self.tools.workspace}
  Files: {file_count}
  Memory entries: {mem_count}"""

        steps = """
Quick start
  1. Inspect your project:
       analyze project
  2. Read a file:
       read file README.md
  3. Search for text:
       find TODO
  4. Get a workflow plan:
       plan
  5. Check system health:
       doctor

When you are ready for ALLINAGENT to change files, start with:
  --allow-write

Shell commands are separately protected and require:
  --allow-shell

Scaffold a new workspace config with:
  allinagent init

You do not need an API key for the local brain. Local mode keeps your
project and prompts on your machine."""

        # Detect empty workspace and offer guidance
        if file_count == 0:
            empty_note = """
NOTE: This workspace appears to be empty.
  - Run 'allinagent init' to create a config file.
  - Or navigate to a project directory and start ALLINAGENT there."""
            return intro + workspace_info + empty_note + steps

        return intro + workspace_info + steps

    def _capabilities(self) -> str:
        return self.tools.capability_report()

    def _summary(self) -> str:
        return self.tools.project_summary()

    def _storage(self) -> str:
        return self.tools.storage_report()

    def _list(self, intent: Intent) -> str:
        return self.tools.list_dir(intent.args[0] if intent.args else ".")

    def _read(self, intent: Intent) -> str:
        if not intent.args:
            return "READ: provide a path, for example: read file README.md"
        return self.tools.read_file(intent.args[0])

    def _search(self, intent: Intent) -> str:
        if not intent.args:
            return "SEARCH: provide text, for example: find TODO"
        return self.tools.search_text(intent.args[0])

    def _status(self) -> str:
        return (
            "ALLINAGENT STATUS\n"
            "- identity: independent local-first agent\n"
            "- local brain: online\n"
            f"- workspace: {self.tools.workspace}\n"
            "- network required for local mode: no\n"
            "- external model required: no\n\n"
            f"{self.tools.capability_report()}"
        )

    def _plan(self) -> str:
        return """ALLINAGENT LOCAL PLAN

1. Inspect the workspace before making assumptions.
2. Identify the smallest useful change.
3. Keep all file access inside the workspace.
4. Read relevant files before editing them.
5. Require explicit write permission before mutations.
6. Require explicit shell permission before command execution.
7. Verify results using local reads and searches.
8. Report what actually happened — never invent a successful edit or command.

Local mode never sends code or prompts to a network service."""

    def _unknown(self) -> str:
        return (
            "ALLINAGENT local brain does not have a deterministic handler for that "
            "request yet. No request was sent off-machine.\n\n"
            "Try 'help' for available commands, or explicitly use --llm for "
            "optional external reasoning."
        )

    def _create_hint(self) -> str:
        return (
            "ALLINAGENT can create websites, games, scripts, and other projects.\n"
            "Examples:\n"
            "  make me a dark gaming website\n"
            "  create a game called DOG GO\n"
            "  build me a Python script\n\n"
            "To actually create files, run with --allow-write."
        )

    def _project_hint(self) -> str:
        return (
            "Project commands:\n"
            "  project view    - Show project context\n"
            "  project status  - Quick status\n"
            "  project files   - List tracked files\n"
            "  project changes - Recent changes\n"
            "  project clear   - Delete project memory\n\n"
            "Create a project first with: make me a website"
        )

    def _limit_output(self, value: str) -> str:
        if len(value) <= self.MAX_OUTPUT:
            return value
        return value[: self.MAX_OUTPUT] + "\n... [output truncated by ALLINAGENT]"

    def explain_intent(self, prompt: str) -> str:
        """Return the classifier decision for debugging and future UI."""
        intent = self._classify(prompt)
        arguments = ", ".join(intent.args) if intent.args else "(none)"
        return (
            f"Intent: {intent.name}\n"
            f"Confidence: {intent.confidence}%\n"
            f"Arguments: {arguments}"
        )

    def build_plan(self, prompt: str) -> list[PlanStep]:
        """Build a deterministic, side-effect-aware plan."""
        intent = self._classify(prompt)
        if intent.name == "summary":
            return [PlanStep("Inspect project", self.tools.project_summary)]
        if intent.name == "storage":
            return [PlanStep("Inspect storage", self.tools.storage_report)]
        if intent.name == "list":
            return [PlanStep("List directory", lambda: self._list(intent))]
        if intent.name == "read":
            return [PlanStep("Read file", lambda: self._read(intent))]
        if intent.name == "search":
            return [PlanStep("Search workspace", lambda: self._search(intent))]
        if intent.name == "status":
            return [PlanStep("Inspect status", self._status)]
        return []

    def run_plan(self, prompt: str) -> str:
        """Execute a deterministic plan and stop cleanly if a step errors."""
        steps = self.build_plan(prompt)
        if not steps:
            return self.run(prompt)

        output: list[str] = []
        for number, step in enumerate(steps, 1):
            output.append(f"[{number}] {step.label}")
            try:
                output.append(step.action())
            except Exception as exc:
                output.append(f"STEP ERROR: {type(exc).__name__}: {exc}")
                break
        return self._limit_output("\n\n".join(output))

    def supports(self, command: str) -> bool:
        return self._classify(command).confidence >= 70

    def available_commands(self) -> tuple[str, ...]:
        return (
            "who are you",
            "help",
            "how do i get started",
            "capabilities",
            "analyze project",
            "list files",
            "read file <path>",
            "find <text>",
            "free up space",
            "status project",
            "plan",
            "doctor",
            "quickstart",
            "make me a website",
            "make me a game",
            "create a script",
            "project view",
            "project status",
            "project clear",
        )


def local_brain_banner(version: str = "0.1.0") -> str:
    """Return a compact banner suitable for the interactive CLI."""
    return (
        f"ALLINAGENT v{version}\n"
        "Local-first. Offline brain active. External models are optional fuel."
    )
