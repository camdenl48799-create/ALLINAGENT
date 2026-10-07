# ALLINAGENT

> **v1.1.0 — Current release**

**An independent, local-first AI coding agent that creates.**
ALLINAGENT is the product. Models are optional fuel.

Turn your ideas into real projects — websites, games, scripts, and more — all on your machine.

## What's new in v1.1.0

This is a major feature update focused on making ALLINAGENT a genuine creation agent:

### Universal Creation System

ALLINAGENT can create real project files from natural-language requests:

```text
"make me a dark gaming website"
"create a game called DOG GO"
"build me a Python script"
```

The agent follows a PLAN → MODIFY → VALIDATE → REPORT workflow and creates actual files in your workspace.

### Website Builder

Generates complete static website projects with HTML, CSS, JavaScript, and a README. Supports follow-up modifications:

```text
"make the buttons bigger"     → modifies CSS
"add a games page"           → creates new HTML page, updates nav
"make it mobile friendly"    → adds responsive CSS
"change the color to blue"   → updates CSS variables
```

### Project Memory

Tracks project name, purpose, technologies, important files, and changes:

```text
project view      → full project context
project status    → quick summary
project files     → tracked files
project changes   → recent modifications
project clear     → delete project memory
```

### File Operations

New safe file operations with guardrails:

- `create_dir` — create directories
- `rename_file` / `move_file` — rename and move files
- `delete_file` — delete with confirmation required
- `edit_file` — find-and-replace text in files
- `write_files` — batch write multiple files

### Safety Guardrails

- Destructive operations require explicit confirmation
- Workspace root deletion is blocked
- Protected directories (.git, .venv, .allinagent) cannot be deleted
- Dangerous shell commands are classified and blocked
- Protected config files cannot be silently overwritten

### Validators

Generated code is validated without dangerous shell calls:

- **Python**: `ast.parse` syntax checking
- **JSON**: `json.loads` validation
- **TOML**: `tomllib` parsing
- **HTML**: structure checks
- **CSS**: rule validation
- **JS**: brace balancing check

### Payment Guidance

Safe guidance for users who want to sell their creations. Payment is never required for normal use. Only shown when the user mentions selling, payment, or monetization.

Security rules:
- Never put API keys in frontend code
- Store credentials in `.env` files (never committed)
- All payment processing happens on the backend

### CLI Improvements

- `allinagent init` — scaffold a workspace config
- `allinagent doctor` — run health diagnostics
- `--version` — print version
- `--json` — structured JSON output
- `--no-color` — disable colored output
- Interactive REPL with `project`, `memory`, `history`, `explain`, `clear` commands

### Cross-Platform Install

- `scripts/install.ps1` — Windows PowerShell
- `scripts/install.sh` — macOS/Linux Bash

## Architecture Overview

```text
User
 |
 v
ALLINAGENT
 ├── Local Brain (deterministic intent router)
 |    ├── Identity, help, onboarding
 |    ├── Workspace tools (read, list, search)
 |    └── Project commands
 |
 ├── Creator System
 |    ├── Website Builder (HTML/CSS/JS generation)
 |    ├── Game Builder (Canvas-based games)
 |    ├── Script Builder (Python)
 |    ├── Document Builder
 |    └── Follow-up Modification (modify existing projects)
 |
 ├── Planner (PLAN → MODIFY → VALIDATE → REPORT)
 |
 ├── Validators (Python, JSON, TOML, HTML, CSS, JS)
 |
 ├── Guardrails (destructive operation classification)
 |
 ├── Project Memory (.allinagent/project.json)
 |
 └── Optional LLM (OpenAI-compatible tool loop)
```

## Module Reference

| Module | Purpose |
|---|---|
| `agent.py` | Main orchestration — routes requests to creator, local brain, or LLM |
| `cli.py` | CLI argument parsing, REPL, init, doctor commands |
| `creator.py` | Universal creation dispatcher |
| `website_builder.py` | Website generation and modification |
| `planner.py` | Task planning with progress summaries |
| `project.py` | Project metadata and context store |
| `validators.py` | File validation (Python, JSON, TOML, HTML, CSS, JS) |
| `guardrails.py` | Safety classification for destructive operations |
| `local_brain.py` | Deterministic offline intent router |
| `tools.py` | Sandboxed workspace tools with file operations |
| `memory.py` | Persistent JSON conversation memory |
| `config.py` | Environment-based configuration |
| `llm.py` | Optional OpenAI-compatible tool loop |
| `prompts.py` | System prompts for external model mode |

## Installation

Requires **Python 3.10+**.

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

### macOS / Linux (Bash)

```bash
bash scripts/install.sh
```

Add to PATH:

```bash
export PATH="$HOME/.local/share/ALLINAGENT/bin:$PATH"
```

### Local development install

```bash
pip install -e .
```

### Optional LLM support

```bash
pip install -e ".[llm]"
```

No API key is required for local mode.

## Configuration

### Environment Variables

| Variable | Purpose | Required |
|---|---|---|
| `ALLINAGENT_API_KEY` | API key for external model | No |
| `ALLINAGENT_BASE_URL` | OpenAI-compatible endpoint URL | No |
| `ALLINAGENT_MODEL` | Model name | No |
| `OPENAI_API_KEY` | Fallback API key (OpenAI compat) | No |
| `NO_COLOR` | Disable colored output | No |

### Workspace Config

Run `allinagent init` to create a `.allinagent.toml`:

```toml
[allinagent]
# model = "gpt-4o"
# base_url = "https://api.openai.com/v1"
# api_key_env = "ALLINAGENT_API_KEY"
```

## Usage

### Create a website

```bash
allinagent --allow-write "make me a dark gaming website"
```

### Follow-up modifications

```bash
allinagent --allow-write "make the buttons bigger"
allinagent --allow-write "add a games page"
allinagent --allow-write "make it mobile friendly"
```

### Interactive REPL

```bash
allinagent -i
```

### Run a one-shot task

```bash
allinagent analyze project
```

### JSON output

```bash
allinagent --json "who are you"
```

### Use another workspace

```bash
allinagent --workspace ./my-project analyze project
```

### Project management

```bash
allinagent "project view"
allinagent "project changes"
allinagent "project clear"
```

### Diagnostics

```bash
allinagent doctor
```

## Safety

ALLINAGENT is safe-by-default:

- File paths cannot escape the workspace sandbox
- File writes require `--allow-write`
- Shell execution requires `--allow-shell`
- `--dry-run` blocks all mutations
- File deletion requires explicit confirmation
- Workspace root cannot be deleted
- Protected directories (.git, .venv, .allinagent) are blocked from deletion
- Protected config files cannot be silently overwritten
- Dangerous shell commands are detected and blocked
- Payment credentials are never exposed in frontend code
- Local mode does not send code or prompts to external services

## CLI Options

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

## Local Commands

```text
who are you
help
how do I get started?
capabilities
analyze project
list files
read file <path>
find <text>
free up space
status project
plan
doctor
quickstart
make me a website
make me a game
create a script
project view
project status
project clear
```

## REPL Commands

```text
help                 Show REPL help
clear                Clear the screen
memory               Show memory status
memory clear         Clear saved memory
project view         Show project context
project status       Quick project status
project files        List tracked files
project changes      Recent changes
project clear         Delete project memory
history              Show conversation history
status               Show workspace status
explain <prompt>     Show intent classification
exit, quit           Exit the REPL
```

## Project Structure

```text
ALLINAGENT/
├── allinagent/
│   ├── __init__.py
│   ├── __main__.py
│   ├── agent.py
│   ├── cli.py
│   ├── config.py
│   ├── creator.py
│   ├── guardrails.py
│   ├── llm.py
│   ├── local_brain.py
│   ├── memory.py
│   ├── planner.py
│   ├── project.py
│   ├── prompts.py
│   ├── tools.py
│   ├── validators.py
│   └── website_builder.py
├── scripts/
│   ├── install.ps1
│   └── install.sh
├── tests/
│   ├── test_local_agent.py
│   ├── test_cli_features.py
│   └── test_v1_1_0.py
├── pyproject.toml
└── README.md
```

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/ -v

# Compile check
python -m compileall allinagent

# Build wheel
python -m pip wheel . -w /tmp/dist

# Run diagnostics
allinagent doctor
```

Workflow:

```text
inspect → plan → modify → validate → report
```

Core rule:

> **Local capability first. External services are always opt-in.**

## Troubleshooting

### "WRITE DENIED" errors

File writes require `--allow-write`:

```bash
allinagent --allow-write "your task"
```

### "DELETE: confirmation required"

Deletion requires explicit confirmation. This is a safety feature.

### "Path escapes workspace" errors

ALLINAGENT sandboxes all file operations to the configured workspace. Use `--workspace` to set a different workspace:

```bash
allinagent --workspace ./my-project "your task"
```

### External LLM not working

Ensure the `openai` package is installed and API key is set:

```bash
pip install -e ".[llm]"
export ALLINAGENT_API_KEY="your-key"
allinagent --llm "your task"
```

### Tests failing

Ensure the package is installed in development mode:

```bash
pip install -e .
python -m pytest tests/ -v
```

## Security Notes

- ALLINAGENT does not send code or prompts to external services in local mode
- All file operations are sandboxed to the workspace
- Payment credentials are never stored or transmitted by ALLINAGENT
- `.env` files should be added to `.gitignore`
- Never put API keys, secret keys, or passwords in frontend code
- The `--dry-run` flag can be used to preview changes without writing

## Limitations

- No graphical/web UI — ALLINAGENT is a CLI tool. A full browser IDE is a future target.
- The local brain is deterministic, not a foundation model. For complex reasoning, use `--llm`.
- Website generation uses vanilla HTML/CSS/JS by default. React/Next.js support requires the optional LLM.
- Game generation produces Canvas-based browser games, not native apps.
- Desktop app generation is not supported in v1.1.0.

## Roadmap (v1.2.0+)

- Browser-based IDE interface (chat, file explorer, code editor, preview)
- Git-aware tools and version control integration
- Streaming LLM mode
- React/Next.js project generation
- Desktop app generation (Electron/Tauri)
- Plugin/MCP hooks
- Configuration file support (.allinagent.toml)
- Smarter multi-step local reasoning

## License

MIT License.

**ALLINAGENT — Independent. Local-first. Honest. Built to create.**
