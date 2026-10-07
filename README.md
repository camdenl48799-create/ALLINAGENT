# ALLINAGENT

> **v1.2.5 — Current release**

**An independent, local-first AI creation and development agent.**
Turn your ideas into real projects — websites, games, scripts, and documents — all on your machine.

## What's New in v1.2.5

This is a major upgrade that makes ALLINAGENT approximately 3× more capable than v1.1.0:

### Smarter Understanding

A new `RequestAnalyzer` converts natural-language requests into structured task specifications. Instead of keyword matching, it understands multi-part requests like:

> "Make me a gaming website for my company with a homepage, products page, login page, dark mode, animations, contact form, and an admin dashboard."

It extracts pages, features, theme, tech preferences, and project name from a single prompt.

### Project Inspection

Before modifying any project, ALLINAGENT inspects the workspace to determine project type, languages, frameworks, dependencies, entry points, config files, tests, and important files. It never blindly overwrites existing work.

### Checkpoint & Rollback

Create snapshots before major changes and safely undo them:

```bash
checkpoint    # Create a snapshot
changes       # See what changed
diff <path>   # See file-level diff
rollback      # Undo to last checkpoint
```

### Autonomous Build-Test-Fix Loop

A bounded loop that plans, builds, validates, detects errors, attempts fixes, and re-validates. Configurable limits prevent infinite loops.

### Expanded Website Builder

Multi-page websites with navigation, landing pages, login UI, contact forms, product pages, dark/light themes, animations, responsive layouts, and reusable components.

### Expanded Game Builder

Playable browser games with HTML5 Canvas: player movement, enemies, health, score, levels, pause menu, restart, win/lose states, difficulty selection, and settings.

### Document Builder

Generates specific, useful documents: README, technical specification, user guide, manual, changelog, and project plan — based on the actual request and project context.

### Tool Registry

A unified registry that provides tool schemas, descriptions, permission metadata, and risk levels for both the local brain and optional LLM tool loop.

### Enhanced Memory

Project memory tracks architecture, completed features, pending tasks, known bugs, requirements, decisions, and recent changes. Supports `--no-memory` to disable storage.

### Progress Reporting

Concise progress summaries during operations: "Planning...", "Creating files...", "Running validation...", "Checking for errors...", "Completed."

## Architecture Overview

```text
User Request
    |
    v
Request Analyzer (natural language -> TaskSpec)
    |
    v
Agent (orchestrator)
    |
    +-- Inspector (project analysis)
    +-- Checkpoint Manager (snapshots)
    +-- Creator System
    |    +-- Website Builder
    |    +-- Game Builder
    |    +-- Document Builder
    |    +-- Script Builder
    +-- Planner / Autonomous Loop
    +-- Tool Registry (unified tool schemas)
    +-- Validators (Python, JSON, TOML, HTML, CSS, JS)
    +-- Guardrails (destructive operation protection)
    +-- Project Memory (.allinagent/project.json)
    +-- Conversation Memory (.allinagent-memory.json)
    +-- Optional LLM (OpenAI-compatible)
```

## Module Reference

| Module | Purpose |
|---|---|
| `agent.py` | Main orchestration — routes requests through the full pipeline |
| `understanding.py` | Request analyzer — natural language to structured TaskSpec |
| `inspector.py` | Project inspection — detects type, languages, frameworks, deps |
| `checkpoint.py` | Checkpoint/rollback system — snapshot, restore, diff |
| `autoloop.py` | Autonomous build-test-fix loop with bounded retries |
| `tool_registry.py` | Unified tool registry with schemas and permission metadata |
| `creator.py` | Universal creation dispatcher |
| `website_builder.py` | Multi-page website generation and modification |
| `game_builder.py` | Playable browser game generation |
| `document_builder.py` | Document generation (README, spec, guide, manual, changelog, plan) |
| `planner.py` | Task planning with progress summaries |
| `project.py` | Project metadata and context store |
| `validators.py` | File validation (Python ast, JSON, TOML, HTML, CSS, JS) |
| `guardrails.py` | Destructive operation classification and protection |
| `local_brain.py` | Deterministic offline intent router |
| `tools.py` | Sandboxed workspace tools with file operations |
| `memory.py` | Persistent conversation memory |
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

### Local development install

```bash
pip install -e .
```

### Optional LLM support

```bash
pip install -e ".[llm]"
```

No API key is required for local mode.

## Usage Examples

### Create a website

```bash
allinagent --allow-write "make me a dark gaming website"
```

### Create a complex multi-page website

```bash
allinagent --allow-write "make me a gaming website with a homepage, products page, login page, and contact form"
```

### Follow-up modifications

```bash
allinagent --allow-write "make the buttons bigger"
allinagent --allow-write "add a games page"
allinagent --allow-write "make it mobile friendly"
allinagent --allow-write "change the color to blue"
```

### Create a game

```bash
allinagent --allow-write "make me a game"
```

### Create a document

```bash
allinagent --allow-write "create a readme for my project"
allinagent --allow-write "create a technical specification"
allinagent --allow-write "create a user guide"
```

### Inspect a project

```bash
allinagent inspect
```

### Checkpoints and rollback

```bash
allinagent checkpoint
allinagent changes
allinagent diff src/main.py
allinagent rollback
```

### Interactive REPL

```bash
allinagent -i
```

### JSON output

```bash
allinagent --json "analyze project"
```

### Diagnostics

```bash
allinagent doctor
```

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
| `--no-memory` | Disable memory storage |
| `--json` | Output as JSON (one-shot mode) |

## Commands

```text
who are you          Identity and capabilities
help                 Show all commands
inspect              Inspect project structure
doctor               Run diagnostics
checkpoint           Create a snapshot
rollback             Undo to last checkpoint
changes              Show changes since checkpoint
diff <path>          Show file diff
project view         Show project context
project status       Quick status
project clear        Delete project memory
memory               Memory status
memory view          Show conversation memory
memory clear         Clear conversation memory
history              Show recent history
status               Workspace status
plan                 Local workflow guide

make me a website    Create a website
make me a game       Create a game
create a script       Create a script
create a document     Create a document
```

## Safety

ALLINAGENT is safe-by-default:

- Path sandbox enforced on all operations
- File writes require `--allow-write`
- Shell execution requires `--allow-shell`
- `--dry-run` blocks all mutations
- File deletion requires explicit confirmation
- Workspace root and protected directories cannot be deleted
- Protected config files cannot be silently overwritten
- Dangerous shell commands are blocked (rm -rf, mkfs, shutdown, etc.)
- Checkpoints before major changes allow safe rollback
- Payment credentials are never exposed in frontend code
- `--no-memory` disables all memory storage
- Local mode does not send code or prompts to external services

## Configuration

### Environment Variables

| Variable | Purpose | Required |
|---|---|---|
| `ALLINAGENT_API_KEY` | API key for external model | No |
| `ALLINAGENT_BASE_URL` | Model endpoint URL | No |
| `ALLINAGENT_MODEL` | Model name | No |
| `OPENAI_API_KEY` | Fallback API key | No |
| `NO_COLOR` | Disable colored output | No |

### Workspace Config

Run `allinagent init` to create `.allinagent.toml`.

## Project Structure

```text
ALLINAGENT/
├── allinagent/
│   ├── __init__.py          (v1.2.5)
│   ├── __main__.py
│   ├── agent.py             (orchestrator)
│   ├── understanding.py      (request analyzer)
│   ├── inspector.py         (project inspection)
│   ├── checkpoint.py        (checkpoint/rollback)
│   ├── autoloop.py          (build-test-fix loop)
│   ├── tool_registry.py     (unified tool schemas)
│   ├── creator.py           (creation dispatcher)
│   ├── website_builder.py   (website generation)
│   ├── game_builder.py      (game generation)
│   ├── document_builder.py  (document generation)
│   ├── planner.py           (task planning)
│   ├── project.py           (project memory)
│   ├── validators.py        (file validation)
│   ├── guardrails.py        (safety classification)
│   ├── local_brain.py       (deterministic intent router)
│   ├── tools.py             (sandboxed file operations)
│   ├── memory.py            (conversation memory)
│   ├── config.py            (configuration)
│   ├── llm.py               (optional LLM loop)
│   └── prompts.py            (system prompts)
├── scripts/
│   ├── install.ps1
│   └── install.sh
├── tests/
│   ├── test_local_agent.py
│   ├── test_cli_features.py
│   ├── test_safety.py
│   ├── test_v1_1_0.py
│   └── test_v1_2_5.py
├── pyproject.toml
└── README.md
```

## Development

```bash
pip install -e .
python -m pytest tests/ -v
python -m compileall allinagent
python -m pip wheel . -w /tmp/dist
allinagent --version
allinagent doctor
```

Workflow: `inspect → plan → build → validate → fix → report`

## Limitations

- No graphical/web UI — ALLINAGENT is a CLI tool
- Local brain is deterministic, not a foundation model — use `--llm` for complex reasoning
- Website generation uses vanilla HTML/CSS/JS (no JS build system)
- Game generation produces Canvas-based browser games
- Desktop app generation is not supported
- Autonomous error fixing is limited to detection and reporting

## Roadmap (v1.3.0+)

- Browser-based IDE interface
- Git integration
- Streaming LLM mode
- React/Next.js project generation
- Auto-fix error recovery loop
- Plugin/MCP hooks
- Desktop app generation

## License

MIT License.

**ALLINAGENT v1.2.5 — Independent. Local-first. Honest. Built to create.**
