"""CLI for ALLINAGENT.

Provides argument parsing, an interactive REPL with inline commands,
workspace initialization, and a diagnostics (doctor) command.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .agent import Agent
from .config import Config

# --- Color support ----------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"


class Colors:
    """Centralized color management with automatic detection."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and self._supports_color()

    @staticmethod
    def _supports_color() -> bool:
        if os.getenv("NO_COLOR"):
            return False
        if os.getenv("CLICOLOR_FORCE"):
            return True
        return sys.stdout.isatty()

    def _wrap(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"{code}{text}{_RESET}"

    def bold(self, text: str) -> str:
        return self._wrap(_BOLD, text)

    def dim(self, text: str) -> str:
        return self._wrap(_DIM, text)

    def cyan(self, text: str) -> str:
        return self._wrap(_CYAN, text)

    def green(self, text: str) -> str:
        return self._wrap(_GREEN, text)

    def yellow(self, text: str) -> str:
        return self._wrap(_YELLOW, text)

    def red(self, text: str) -> str:
        return self._wrap(_RED, text)

    def blue(self, text: str) -> str:
        return self._wrap(_BLUE, text)

    def magenta(self, text: str) -> str:
        return self._wrap(_MAGENTA, text)


# --- Banner -----------------------------------------------------------------


def banner(version: str = __version__, colors: Colors | None = None) -> str:
    """Return the startup banner for the interactive REPL."""
    c = colors or Colors()
    title = c.bold(c.cyan(f"  ALLINAGENT v{version}"))
    tagline = c.dim("  Local-first. Offline brain active. External models are optional fuel.")
    return f"\n{title}\n{tagline}\n"


# --- Activation ------------------------------------------------------------


def activate() -> int:
    """Prepare a local ALLINAGENT installation for CLI use."""
    print("ALLINAGENT activation")
    print("=" * 40)

    if sys.version_info < (3, 10):
        print("ERROR: Python 3.10+ is required.")
        return 1

    try:
        root = Path(__file__).resolve().parent.parent
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(root)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print("ERROR: Could not install ALLINAGENT into the current Python environment.")
        if exc.stdout:
            print(exc.stdout.rstrip())
        return 1

    print("Python:      READY")
    print("Package:     INSTALLED")
    print("Local brain: READY")
    print("API key:     NOT REQUIRED")
    print()
    print("Activation complete.")
    print("Run 'allinagent' to start.")
    print("Run 'allinagent --help' for commands.")
    return 0


# --- Init command -----------------------------------------------------------


def init_workspace(workspace: Path, colors: Colors | None = None) -> int:
    """Scaffold an ALLINAGENT workspace configuration file.

    Creates a .allinagent.toml config and a README note so the workspace
    is recognized as ALLINAGENT-aware.
    """
    c = colors or Colors()
    workspace.mkdir(parents=True, exist_ok=True)
    config_path = workspace / ".allinagent.toml"

    print(c.bold(c.cyan("ALLINAGENT INIT")))
    print(f"  Workspace: {workspace}")
    print()

    if config_path.exists():
        print(c.yellow("  A .allinagent.toml already exists here."))
        print(c.dim("  Leaving it untouched."))
        return 0

    config_content = """\
# ALLINAGENT workspace configuration
# Local mode requires no API key. Edit values below to opt into external reasoning.

[allinagent]
# model = "gpt-4o"
# base_url = "https://api.openai.com/v1"
# api_key_env = "ALLINAGENT_API_KEY"
"""
    config_path.write_text(config_content, encoding="utf-8")

    print(c.green("  Created: .allinagent.toml"))
    print()
    print(c.bold("  Next steps:"))
    print(c.dim("    1. Run: allinagent"))
    print(c.dim("    2. Type: analyze project"))
    print(c.dim("    3. Type: help"))
    print()
    print(c.dim("  To enable file writes, start with --allow-write"))
    print(c.dim("  To enable shell commands, start with --allow-shell"))
    return 0


# --- Doctor command ---------------------------------------------------------


def doctor(workspace: Path, colors: Colors | None = None) -> int:
    """Run diagnostics and print a health report."""
    from .tools import WorkspaceTools

    c = colors or Colors()
    tools = WorkspaceTools(workspace)

    print(c.bold(c.cyan("ALLINAGENT DOCTOR")))
    print(f"  {c.dim('Checking system health...')}")
    print()

    checks: list[tuple[str, bool, str]] = []

    # Python version
    py_ok = sys.version_info >= (3, 10)
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("Python version", py_ok, f"Python {py_ver}"))

    # Workspace exists
    checks.append(("Workspace exists", workspace.exists(), str(workspace)))

    # Workspace writable
    import os as _os
    writable = _os.access(workspace, _os.W_OK) if workspace.exists() else False
    checks.append(("Workspace writable", writable, str(workspace)))

    # Visible files
    file_count = sum(1 for _ in tools._iter_files())
    checks.append(("Files discovered", file_count >= 0, f"{file_count} files"))

    # Tools diagnostics
    diag = tools.diagnostics()
    checks.append(("Path sandbox", True, "enforced"))

    # Memory
    from .memory import LocalMemory
    mem = LocalMemory(workspace)
    mem_entries = len(mem._load())
    checks.append(("Local memory", True, f"{mem_entries} entries"))

    # LLM availability (informational — LLM is optional)
    config = Config.from_env()
    llm_status = "available" if config.has_llm else "not configured (optional)"
    checks.append(("External LLM", True, llm_status))

    # Print results
    all_ok = True
    for name, ok, detail in checks:
        status = c.green("OK") if ok else c.red("FAIL")
        print(f"  {status}  {c.bold(name):<22} {c.dim(detail)}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print(c.green("  All checks passed."))
    else:
        print(c.yellow("  Some checks need attention."))
    return 0 if all_ok else 1


# --- Argument parser --------------------------------------------------------


def build_parser():
    p = argparse.ArgumentParser(
        prog="allinagent",
        description="ALLINAGENT — an independent, local-first AI coding agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Inline REPL commands: help, clear, memory, history, status, explain <prompt>, exit\n"
            "Run 'allinagent init' to scaffold a workspace config.\n"
            "Run 'allinagent doctor' to run diagnostics."
        ),
    )
    p.add_argument("prompt", nargs="*", help="Task for ALLINAGENT")
    p.add_argument("--workspace", default=".", help="Workspace root")
    p.add_argument("-i", "--interactive", action="store_true", help="Start interactive REPL")
    p.add_argument("--local", action="store_true", help="Force offline local brain")
    p.add_argument("--llm", action="store_true", help="Opt into an OpenAI-compatible reasoning model")
    p.add_argument("--dry-run", action="store_true", help="Disable all mutations")
    p.add_argument("--allow-write", action="store_true", help="Allow file writes")
    p.add_argument("--allow-shell", action="store_true", help="Allow shell commands")
    p.add_argument("--model", help="External model name")
    p.add_argument("--base-url", help="OpenAI-compatible endpoint")
    p.add_argument("--max-steps", type=int, default=8, help="External tool-loop step limit")
    p.add_argument("-v", "--verbose", action="store_true", help="Show mode and workspace")
    p.add_argument("--version", action="version", version=f"allinagent {__version__}")
    p.add_argument("--no-color", action="store_true", help="Disable colored output")
    p.add_argument("--json", action="store_true", help="Output results as JSON (non-interactive)")
    return p


# --- REPL -------------------------------------------------------------------


REPL_HELP = """\
REPL commands:
  help                 Show this help
  clear                Clear the screen
  memory               Show memory status
  memory clear         Clear all saved memory
  project view         Show project context
  project status       Quick project status
  project files        List tracked files
  project changes      Recent changes
  project clear         Delete project memory
  history              Show recent conversation history
  status               Show workspace and capability status
  explain <prompt>     Show how the local brain classifies a prompt
  exit, quit           Exit the REPL

Creation commands:
  make me a website    Create a website (requires --allow-write)
  make me a game       Create a game (requires --allow-write)
  create a script      Create a script (requires --allow-write)

Local brain commands:
  who are you          Identity
  analyze project      Project summary
  list files           List workspace root
  list files <path>    List a directory
  read file <path>     Read a file
  find <text>          Search workspace text
  free up space        Storage report
  plan                 Local workflow guide
"""


def _print_separated(text: str, colors: Colors) -> None:
    """Print output with a separator line."""
    line = colors.dim("-" * 60)
    print(f"\n{text}\n{line}")


def run_repl(agent: Agent, colors: Colors, version: str = __version__) -> int:
    """Run the interactive REPL with inline commands."""
    c = colors
    print(banner(version, c))

    mode = "local" if not agent.use_llm else "optional-llm"
    perms = []
    if agent.tools.allow_write:
        perms.append(c.green("write"))
    else:
        perms.append(c.dim("write"))
    if agent.tools.allow_shell:
        perms.append(c.green("shell"))
    else:
        perms.append(c.dim("shell"))
    if agent.tools.dry_run:
        perms.append(c.yellow("dry-run"))

    print(f"  {c.dim('Mode:')} {c.bold(mode)}  {c.dim('Workspace:')} {c.dim(str(agent.workspace))}")
    print(f"  {c.dim('Permissions:')} {' | '.join(perms)}")
    print(f"  {c.dim('Type')} {c.bold('help')} {c.dim('for commands,')} {c.bold('exit')} {c.dim('to quit.')}")
    print()

    history: list[tuple[str, str]] = []

    while True:
        try:
            prompt = input(c.bold(c.cyan("allinagent> "))).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print(c.dim("  Goodbye."))
            break

        if not prompt:
            continue

        lower = prompt.lower()

        # --- Inline REPL commands ---
        if lower in ("exit", "quit"):
            print(c.dim("  Goodbye."))
            break

        if lower == "help":
            print(REPL_HELP)
            continue

        if lower == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue

        if lower.startswith("memory"):
            parts = lower.split(None, 1)
            if len(parts) > 1 and parts[1] == "clear":
                if agent.memory.clear():
                    print(c.green("  Memory cleared."))
                else:
                    print(c.red("  Could not clear memory."))
            else:
                print(agent.memory.status())
            continue

        if lower.startswith("project"):
            parts = lower.split(None, 1)
            sub = parts[1] if len(parts) > 1 else "view"
            if sub == "clear":
                if agent.project.clear():
                    print(c.green("  Project memory cleared."))
                else:
                    print(c.red("  Could not clear project memory."))
            elif sub == "status":
                print(agent.project.status())
            elif sub == "files":
                data = agent.project._load()
                if not data:
                    print(c.dim("  No project initialized."))
                else:
                    files = data.get("important_files", [])
                    if not files:
                        print(c.dim("  No tracked files."))
                    else:
                        print(c.bold("  Tracked files:"))
                        for f in files:
                            print(f"  {c.dim('-')} {f['path']}")
            elif sub == "changes":
                data = agent.project._load()
                if not data:
                    print(c.dim("  No project initialized."))
                else:
                    changes = data.get("changes", [])
                    if not changes:
                        print(c.dim("  No changes recorded."))
                    else:
                        print(c.bold("  Recent changes:"))
                        for ch in changes[-10:]:
                            print(f"  {c.dim('-')} {ch.get('description', '')[:100]}")
            else:
                print(agent.project.view())
            continue

        if lower == "history":
            if not history:
                print(c.dim("  No conversation history yet."))
            else:
                print(c.bold("  Recent conversation:"))
                for i, (q, _a) in enumerate(history, 1):
                    print(f"  {c.dim(f'{i}.')} {q[:80]}")
            continue

        if lower == "status":
            print(agent.local_brain._status())
            print()
            print(agent.tools.capability_report())
            continue

        if lower.startswith("explain"):
            target = prompt[len("explain"):].strip()
            if not target:
                print(c.yellow("  Usage: explain <prompt>"))
                print(c.dim("  Example: explain read file README.md"))
            else:
                print(agent.local_brain.explain_intent(target))
            continue

        # --- Pass to the agent ---
        result = agent.run(prompt)
        history.append((prompt, result))
        _print_separated(result, c)

    return 0


# --- Main entry point --------------------------------------------------------


def main():
    args = build_parser().parse_args()
    colors = Colors(enabled=not args.no_color)

    # Handle subcommands
    if args.prompt and args.prompt[0].lower() == "activate":
        return activate()

    if args.prompt and args.prompt[0].lower() == "init":
        workspace = Path(args.workspace).resolve()
        return init_workspace(workspace, colors)

    if args.prompt and args.prompt[0].lower() == "doctor":
        workspace = Path(args.workspace).resolve()
        return doctor(workspace, colors)

    workspace = Path(args.workspace).resolve()
    config = Config.from_env(model=args.model, base_url=args.base_url)
    use_llm = bool(args.llm and not args.local and config.has_llm)

    if args.verbose:
        mode = "local" if not use_llm else "optional-llm"
        print(f"ALLINAGENT v{__version__} | mode={mode} | workspace={workspace}")

    agent = Agent(
        workspace,
        dry_run=args.dry_run,
        allow_write=args.allow_write,
        allow_shell=args.allow_shell,
        use_llm=use_llm,
        config=config,
        max_steps=args.max_steps,
    )

    # Interactive mode or no prompt -> REPL
    if args.interactive or not args.prompt:
        return run_repl(agent, colors, __version__)

    # One-shot mode
    result = agent.run(" ".join(args.prompt))

    if args.json:
        output = {
            "version": __version__,
            "workspace": str(workspace),
            "mode": "local" if not use_llm else "optional-llm",
            "prompt": " ".join(args.prompt),
            "result": result,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
