import argparse
from pathlib import Path
from .agent import Agent


def main():
    parser = argparse.ArgumentParser(prog="allinagent", description="ALLINAGENT — a local-first AI coding agent")
    parser.add_argument("prompt", nargs="*", help="Task for the agent")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    parser.add_argument("--dry-run", action="store_true", help="Inspect only; do not modify files")
    args = parser.parse_args()

    agent = Agent(Path(args.workspace).resolve(), dry_run=args.dry_run)
    if not args.prompt:
        print("ALLINAGENT v0.1.0")
        print("Try: python -m allinagent \"analyze this project\"")
        return
    result = agent.run(" ".join(args.prompt))
    print(result)

if __name__ == "__main__":
    main()
