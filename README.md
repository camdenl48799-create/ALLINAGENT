# ALLINAGENT

> **v0.7.2 — Current release**

**An independent, local-first AI coding agent.**  
ALLINAGENT is the product. Models are optional fuel.

Your code stays on your machine in local mode unless you explicitly choose an external model.

## ⚡ Features

- 🧠 Offline local brain — no API key required
- 🛠️ Sandboxed workspace tools
- 💻 CLI + interactive REPL
- 🔒 Writes and shell commands are opt-in
- 🧪 Dry-run mode
- 🔎 Project summaries, file reading, search, storage reports
- 🤖 Optional OpenAI-compatible reasoning
- 🪶 Small Python codebase
- 📜 MIT licensed

## 🏗️ How it works

```text
You
 │
 ▼
ALLINAGENT
 ├── Local Brain ──► Workspace Tools
 │                    └── Offline
 │
 └── Optional LLM
       └── External reasoning (opt-in)
```

The local brain is a deterministic offline intent engine. It is not presented as a foundation model.

## 🚀 Installation

Requires **Python 3.10+**.

### Windows

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

### Local development install

```bash
pip install -e .
```

### Optional LLM support

```bash
pip install -e ".[llm]"
```

No API key is required for local mode.

## 🆕 New here?

Start ALLINAGENT and type:

```text
how do I get started?
```

It will walk you through the basics.

## 🎮 Basic usage

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

## 🛡️ Safety

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

## 🤖 Optional external reasoning

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

## 📋 Local commands

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
```

## ⚙️ CLI options

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

## 📁 Project structure

```text
ALLINAGENT/
├── allinagent/
│   ├── agent.py
│   ├── cli.py
│   ├── config.py
│   ├── llm.py
│   ├── local_brain.py
│   ├── prompts.py
│   └── tools.py
├── scripts/
│   └── install.ps1
├── tests/
├── pyproject.toml
└── README.md
```

## 🧭 Roadmap

- Smarter multi-step local reasoning
- Persistent offline project memory
- Git-aware tools
- Better REPL UX
- Streaming optional LLM mode
- More automated tests
- Optional configuration file
- Plugin/MCP hooks without losing local-first behavior

## 🔧 Development

Keep the workflow simple:

```text
inspect → plan → implement → test → verify → report
```

Core rule:

> **Local capability first. External services are always opt-in.**

## 📜 License

MIT License.

**ALLINAGENT — Independent. Local-first. Honest. Built to code.**
