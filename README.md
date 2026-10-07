# ALLINAGENT

> **v1.1.0 — Current release**

**An independent, local-first AI coding agent.**  
ALLINAGENT is the product. Models are optional fuel.

Your code stays on your machine in local mode unless you explicitly choose an external model.

## Features

- Offline local brain — no API key required
- Sandboxed workspace tools
- CLI + interactive REPL with inline commands
- Writes and shell commands are opt-in
- Dry-run mode
- Project summaries, file reading, search, storage reports
- Optional OpenAI-compatible reasoning
- Persistent local project/conversation memory
- Workspace init scaffolding and diagnostics
- Cross-platform install scripts (Windows + macOS/Linux)
- JSON output mode for scripting
- MIT licensed

## How it works

```text
You
 |
 v
ALLINAGENT
 ├── Local Brain --> Workspace Tools
 |                    └── Offline
 |
 └── Optional LLM
       └── External reasoning (opt-in)
```

The local brain is a deterministic offline intent engine. It is not presented as a foundation model.

## Installation

Requires **Python 3.10+**.

### Windows (PowerShell)

From a cloned/downloaded repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

The bootstrap installer creates an isolated environment under:

```text
%LOCALAPPDATA%\ALLINAGENT
```

Then add its `bin` folder to your PATH and run:

```powershell
allinagent activate
```

### macOS / Linux (Bash)

From a cloned/downloaded repository:

```bash
bash scripts/install.sh
```

The installer creates an isolated venv under:

```text
~/.local/share/ALLINAGENT
```

Add the `bin` folder to your PATH:

```bash
export PATH="$HOME/.local/share/ALLINAGENT/bin:$PATH"
```

Add that line to your `~/.bashrc` or `~/.zshrc` to make it permanent.

### Local development install

```bash
pip install -e .
```

### Optional LLM support

```bash
pip install -e ".[llm]"
```

No API key is required for local mode.

## New here?

Start ALLINAGENT and type:

```text
how do I get started?
```

It will walk you through the basics, detect your workspace state, and suggest next steps.

Or scaffold a workspace config:

```bash
allinagent init
```

And run diagnostics:

```bash
allinagent doctor
```

## Basic usage

Start in the current folder:

```bash
allinagent
```

Run a task:

```bash
allinagent analyze project
```

Interactive mode:

```bash
allinagent -i
```

Use another workspace:

```bash
allinagent --workspace ./my-project analyze project
```

Force offline mode:

```bash
allinagent --local "analyze project"
```

JSON output (for scripting):

```bash
allinagent --json "analyze project"
```

Disable color:

```bash
allinagent --no-color "analyze project"
```

Check version:

```bash
allinagent --version
```

## REPL inline commands

When in interactive mode (`allinagent -i` or just `allinagent`), these commands are available:

```text
help                 Show REPL help
clear                Clear the screen
memory               Show memory status
memory clear         Clear all saved memory
history              Show recent conversation history
status               Show workspace and capability status
explain <prompt>     Show how the local brain classifies a prompt
exit, quit           Exit the REPL
```

## Safety

ALLINAGENT is safe-by-default:

- File paths cannot escape the workspace.
- File writes require `--allow-write`.
- Shell execution requires `--allow-shell`.
- `--dry-run` blocks mutations even when permissions are enabled.
- Local mode does not send code or prompts to an external service.
- Tool results are reported honestly.

Examples:

```bash
allinagent --allow-write "your task"
allinagent --allow-shell "your task"
allinagent --dry-run "your task"
```

## Optional external reasoning

Configure an OpenAI-compatible endpoint with:

```text
ALLINAGENT_API_KEY
ALLINAGENT_BASE_URL
ALLINAGENT_MODEL
```

`OPENAI_API_KEY` is also accepted for compatibility.

Example:

```bash
allinagent --llm --model your-model "inspect this project"
```

If external reasoning fails, ALLINAGENT falls back to its local brain.

## Local commands

```text
who are you
help
how do I get started?
how do I set this up?
capabilities
analyze project
list files
list files <path>
read file <path>
find <text>
free up space
status project
plan
doctor
quickstart
```

## CLI options

| Option | Purpose |
|---|---|
| `--workspace PATH` | Set the workspace |
| `-i, --interactive` | Start the REPL |
| `--local` | Force offline mode |
| `--llm` | Opt into external reasoning |
| `--dry-run` | Disable mutations |
| `--allow-write` | Enable file writes |
| `--allow-shell` | Enable shell commands |
| `--model NAME` | Select external model |
| `--base-url URL` | Select endpoint |
| `--max-steps N` | Limit LLM tool steps |
| `-v, --verbose` | Show startup details |
| `--version` | Print version and exit |
| `--no-color` | Disable colored output |
| `--json` | Output as JSON (one-shot mode) |

## Project structure

```text
ALLINAGENT/
├── allinagent/
│   ├── __init__.py
│   ├── __main__.py
│   ├── agent.py
│   ├── cli.py
│   ├── config.py
│   ├── llm.py
│   ├── local_brain.py
│   ├── memory.py
│   ├── prompts.py
│   └── tools.py
├── scripts/
│   ├── install.ps1
│   └── install.sh
├── tests/
│   └── test_local_agent.py
├── pyproject.toml
└── README.md
```

## v1.1.0

This release improves the CLI and onboarding experience:

- **Workspace-aware onboarding** — the getting started flow now detects your workspace state (file count, memory entries) and adjusts guidance accordingly, including a note for empty workspaces.
- **`init` command** — `allinagent init` scaffolds a `.allinagent.toml` config file in the workspace.
- **`doctor` command** — `allinagent doctor` runs health checks: Python version, workspace access, file discovery, memory, and LLM configuration.
- **Interactive REPL commands** — added `help`, `clear`, `memory`, `memory clear`, `history`, `status`, and `explain <prompt>` as inline REPL commands.
- **Color support** — colored output with `--no-color` to disable. Auto-detects terminal support and respects `NO_COLOR`.
- **`--version` flag** — print the installed version.
- **`--json` output** — one-shot mode can output structured JSON for scripting and integration.
- **Cross-platform install** — added `scripts/install.sh` for macOS/Linux alongside the existing PowerShell script.
- **Improved intent matching** — added aliases like `cat`, `ls`, `dir`, `grep`, `quickstart`, `disk usage`, and `what is allinagent`.
- **Fixed** the literal `\n` syntax error in `__init__.py` and the README that made the package unimportable.

## Roadmap

- Smarter multi-step local reasoning
- Persistent offline project memory
- Git-aware tools
- Better REPL UX
- Streaming optional LLM mode
- More automated tests
- Optional configuration file
- Plugin/MCP hooks without losing local-first behavior

## Development

Keep the workflow simple:

```text
inspect -> plan -> implement -> test -> verify -> report
```

Core rule:

> **Local capability first. External services are always opt-in.**

## License

MIT License.

**ALLINAGENT — Independent. Local-first. Honest. Built to code.**
