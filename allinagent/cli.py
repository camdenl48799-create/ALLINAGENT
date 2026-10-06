"""CLI for ALLINAGENT."""
from __future__ import annotations
import argparse
from pathlib import Path
from . import __version__
from .agent import Agent
from .config import Config

def build_parser():
    p = argparse.ArgumentParser(prog="allinagent", description="ALLINAGENT — an independent, local-first AI coding agent.")
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
    return p

def main():
    args = build_parser().parse_args()
    workspace = Path(args.workspace).resolve()
    config = Config.from_env(model=args.model, base_url=args.base_url)
    use_llm = bool(args.llm and not args.local and config.has_llm)
    if args.verbose:
        mode = "local" if not use_llm else "optional-llm"
        print(f"ALLINAGENT v{__version__} | mode={mode} | workspace={workspace}")
    agent = Agent(workspace, dry_run=args.dry_run, allow_write=args.allow_write, allow_shell=args.allow_shell, use_llm=use_llm, config=config, max_steps=args.max_steps)
    if args.interactive or not args.prompt:
        print(f"ALLINAGENT v{__version__}")
        print("Local-first. Type help for commands, exit to quit.")
        while True:
            try:
                prompt = input("allinagent> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if prompt.lower() in {"exit", "quit"}:
                break
            if prompt:
                print(agent.run(prompt))
        return
    print(agent.run(" ".join(args.prompt)))

if __name__ == "__main__":
    main()
