from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .agent import Agent
from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="allinagent",
        description="ALLINAGENT — its own local-first AI coding agent",
    )
    p.add_argument("prompt", nargs="*", help="Task for the agent")
    p.add_argument("--workspace", default=".", help="Workspace directory (default: .)")
    p.add_argument("--dry-run", action="store_true", help="Inspect only; no writes or shell")
    p.add_argument("--allow-write", action="store_true", help="Allow write_file tool")
    p.add_argument("--allow-shell", action="store_true", help="Allow run_shell tool")
    p.add_argument("--interactive", "-i", action="store_true", help="REPL mode")
    p.add_argument("--local", action="store_true", help="Force ALLINAGENT local brain (no external model)")
    p.add_argument("--llm", action="store_true", help="Force external model when a key is configured")
    p.add_argument("--model", default=None, help="Override model name")
    p.add_argument("--base-url", default=None, help="Override API base URL")
    p.add_argument("--max-steps", type=int, default=12, help="Max tool rounds per LLM turn")
    p.add_argument("--verbose", "-v", action="store_true", help="Print tool / brain decisions")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def make_agent(args: argparse.Namespace) -> Agent:
    cfg = load_config(model=args.model, base_url=args.base_url, max_steps=args.max_steps)
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"Workspace is not a directory: {workspace}", file=sys.stderr)
        sys.exit(1)
    return Agent(
        workspace,
        cfg,
        dry_run=args.dry_run,
        allow_write=args.allow_write,
        allow_shell=args.allow_shell,
        verbose=args.verbose,
        force_local=args.local,
        force_llm=args.llm,
    )


def run_interactive(agent: Agent) -> None:
    print(agent.status_line())
    print("I am ALLINAGENT. Type a task, or exit / quit / reset / status.")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        low = line.lower()
        if low in {"exit", "quit", "q"}:
            break
        if low == "reset":
            agent.reset_conversation()
            print("(conversation reset)")
            continue
        if low == "status":
            print(agent.status_line())
            continue
        result = agent.run(line)
        print(result)
        print()


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.prompt and not args.interactive:
        print(f"ALLINAGENT v{__version__} — its own local-first AI")
        print('Try: allinagent "who are you"')
        print('     allinagent "analyze this project"')
        print("     allinagent -i")
        print("     allinagent --local \"search TODO\"")
        print("     allinagent --help")
        return

    agent = make_agent(args)

    if args.interactive:
        if args.prompt:
            first = " ".join(args.prompt)
            print(agent.run(first))
            print()
        run_interactive(agent)
        return

    result = agent.run(" ".join(args.prompt))
    print(result)


if __name__ == "__main__":
    main()
