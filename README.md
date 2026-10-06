# ALLINAGENT

> **v0.5.0 — Current release**

> **An independent, local-first AI coding agent.**
>
> **ALLINAGENT is the product. Models are optional fuel.**

ALLINAGENT is a small, open-source coding agent designed around one core idea:

**Your code should stay on your machine unless you explicitly choose otherwise.**

It has an offline local brain, sandboxed workspace tools, a CLI, and an optional OpenAI-compatible reasoning mode. External models are never the identity of ALLINAGENT.

## Why ALLINAGENT?

ALLINAGENT is intentionally different from a cloud-first coding assistant.

- **Local-first:** local mode does not require an API key.
- **Independent identity:** ALLINAGENT does not pretend to be ChatGPT, Claude, Gemini, Copilot, Cursor, or another vendor.
- **Safe by default:** reading is available by default; writing and shell execution require explicit flags.
- **Workspace sandbox:** file paths are prevented from escaping the configured workspace.
- **Optional external reasoning:** OpenAI-compatible endpoints can be used when you explicitly opt in.
- **Honest behavior:** ALLINAGENT reports what its tools actually did instead of claiming fake edits.
- **MIT licensed:** small, readable, and designed to be extended.

## Current architecture

```
You
 │
 ▼
ALLINAGENT
 ├── Local Brain ───────► Workspace Tools
 │        │
 │        └─────────────► Offline / private
 │
 └── Optional LLM ──────► OpenAI-compatible endpoint
              (opt-in fuel only)
```

The local brain is a deterministic intent engine, not a secretly claimed foundation model. It currently handles useful workspace operations locally and provides a clean foundation for richer offline reasoning.

## Features

### Local brain

The offline brain currently understands commands such as:

- `who are you`
- `help`
- `how do I get started?`
- `how do I set this up?`
- `capabilities`
- `analyze project`
- `list files`
- `list files <path>`
- `read file <path>`
- `find <text>`
- `free up space`
- `status project`
- `plan`

Unknown requests stay local and are not silently uploaded.

### Workspace tools

The tool layer provides:

- Project summaries
- File and directory listings
- UTF-8 file reading
- Workspace text search
- Storage reports
- File writes behind explicit permission
- Shell execution behind explicit permission
- Dry-run protection
- Workspace path sandboxing
- Output limits to prevent runaway responses

### Optional reasoning model

ALLINAGENT can optionally use an OpenAI-compatible API endpoint.

Supported configurations can include compatible services such as OpenAI-compatible gateways, local servers, Ollama-style endpoints, LM Studio-style endpoints, Groq-compatible endpoints, or your own compatible server.

The important distinction is:

**The model is a reasoning accelerator. It is not ALLINAGENT's identity.**

## Installation

Requires **Python 3.10+**.

### New here?

If you are not sure what to do, start ALLINAGENT and type:

```text
how do I get started?
```

ALLINAGENT will walk you through the basic setup and usage.

### Windows PowerShell bootstrap

On a fresh Windows machine, use the repository bootstrap installer first:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

The installer downloads the source, creates an isolated environment under `%LOCALAPPDATA%\ALLINAGENT`, installs ALLINAGENT, and verifies the CLI. It does **not** pipe downloaded code into `Invoke-Expression`.

After the bootstrap step, add `%LOCALAPPDATA%\ALLINAGENT\bin` to your PATH. Then the normal activation command is:

```powershell
allinagent activate
```

`allinagent activate` is the installed CLI's setup/verification command; the bootstrap installer is what makes the command available on a completely fresh machine.

### Local-only installation

```bash
pip install -e .
```

This installs ALLINAGENT without requiring the optional OpenAI SDK.

### Optional LLM support

```bash
pip install -e ".[llm]"
```

Local mode remains available even when optional LLM support is installed.

## Basic usage

Run against the current directory:

```bash
allinagent
```

Run a one-shot task:

```bash
allinagent analyze project
```

Start the interactive terminal:

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

Show detailed startup information:

```bash
allinagent -v "status project"
```

## Safety controls

ALLINAGENT intentionally makes powerful operations opt-in.

### Writes

File writes are disabled unless you explicitly enable them:

```bash
allinagent --allow-write "your task"
```

### Shell

Shell execution is disabled unless you explicitly enable it:

```bash
allinagent --allow-shell "your task"
```

### Dry run

Dry-run overrides mutations:

```bash
allinagent --dry-run "your task"
```

You can combine the flags, but `--dry-run` still prevents writes and shell execution.

### Workspace sandbox

ALLINAGENT resolves paths and rejects paths that escape the configured workspace.

For example, a request attempting to access a parent directory outside the workspace is rejected rather than silently followed.

## Optional LLM configuration

Environment variables:

```text
ALLINAGENT_API_KEY
ALLINAGENT_BASE_URL
ALLINAGENT_MODEL
```

For compatibility, `OPENAI_API_KEY` is also recognized as an API-key environment variable.

Example:

```bash
allinagent --llm --model your-model "inspect this project"
```

If the optional external model fails, ALLINAGENT falls back to the local brain rather than crashing the whole agent.

## CLI options

| Option | Purpose |
|---|---|
| `--workspace PATH` | Set the sandboxed workspace |
| `-i, --interactive` | Start the interactive REPL |
| `--local` | Force offline local brain |
| `--llm` | Explicitly opt into external reasoning |
| `--dry-run` | Disable mutations |
| `--allow-write` | Enable file writes |
| `--allow-shell` | Enable shell commands |
| `--model NAME` | Select external model |
| `--base-url URL` | Select OpenAI-compatible endpoint |
| `--max-steps N` | Limit external tool-loop steps |
| `-v, --verbose` | Show mode and workspace |

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
│   ├── prompts.py
│   └── tools.py
├── pyproject.toml
└── README.md
```

## Design principles

1. **Local-first always.**
2. **ALLINAGENT is the product; models are fuel.**
3. **No fake tool results.**
4. **Power requires explicit permission.**
5. **Inspect before changing.**
6. **Keep the implementation readable.**
7. **Prefer complete, shippable functionality over hype.**
8. **Keep the local brain useful even with zero API keys.**
9. **Preserve the MIT license spirit.**

## Roadmap

Planned improvements include:

- Richer multi-step offline reasoning
- Persistent offline project memory
- Git-aware tools
- Git status and diff inspection
- Commit-draft generation
- Better REPL history and modes
- Streaming output for optional LLM mode
- Automated sandbox and local-brain tests
- Optional configuration file support
- MCP/plugin hooks while keeping local-first behavior
- Better documentation and demos
- Context/documentation tooling as an optional capability

## Development

ALLINAGENT is intentionally a small Python project.

A good development workflow is:

```text
inspect → plan → implement → test → verify → report
```

When adding functionality, preserve the core rule:

> **Local capability comes first. External services are opt-in.**

## License

MIT License.

See the repository license file for the complete license text.

---

**ALLINAGENT**

Independent. Local-first. Honest. Built to code.
