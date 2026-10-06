# ALLINAGENT

**Local-first AI coding agent** that works on your machine, in your project folder.

It talks to any OpenAI-compatible API (OpenAI, OpenRouter, Groq, Ollama, LM Studio, vLLM, etc.), uses real tool calling, and stays sandboxed to the workspace you give it.

## Features

- **Real agent loop** — multi-step tool calling with an LLM (not keyword matching)
- **Safe by default** — only operates inside the chosen workspace; write/shell need explicit flags
- **Useful tools** — list files, read, write, search text, project summary, storage report, optional shell
- **One-shot or interactive** — `allinagent "fix the login bug"` or a REPL session
- **Local-first** — point at Ollama / LM Studio / any compatible endpoint; your code stays local

## Requirements

- Python 3.10+
- An API key for an OpenAI-compatible provider (or a local server that needs none)

## Install

```bash
# From the repo
pip install -e .

# Or just run without installing
pip install openai
python -m allinagent --help
```

## Quick start

```bash
export ALLINAGENT_API_KEY=sk-...          # or OPENAI_API_KEY
# Optional overrides:
# export ALLINAGENT_BASE_URL=https://api.openai.com/v1
# export ALLINAGENT_MODEL=gpt-4o-mini

cd /path/to/your/project
allinagent "analyze this project"
allinagent "find the largest files and summarize what can be cleaned safely"
allinagent --interactive                  # REPL
```

### Local models (Ollama example)

```bash
export ALLINAGENT_BASE_URL=http://127.0.0.1:11434/v1
export ALLINAGENT_API_KEY=ollama          # any non-empty string is fine
export ALLINAGENT_MODEL=llama3.2
allinagent "list the Python modules and describe the entry points"
```

### Dry-run (inspect only)

```bash
allinagent --dry-run "propose a cleanup for node_modules and caches"
```

Writes and shell are disabled unless you pass `--allow-write` / `--allow-shell`.

## CLI

```
allinagent [options] [prompt...]

  --workspace PATH     Project root (default: current directory)
  --interactive, -i    Chat REPL until you type exit/quit
  --dry-run            Never modify files or run shell
  --allow-write        Permit write_file
  --allow-shell        Permit run_shell (still sandboxed to workspace)
  --model NAME         Override ALLINAGENT_MODEL
  --base-url URL       Override ALLINAGENT_BASE_URL
  --max-steps N        Max tool rounds per turn (default: 12)
```

## Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `ALLINAGENT_API_KEY` or `OPENAI_API_KEY` | — | API key |
| `ALLINAGENT_BASE_URL` | `https://api.openai.com/v1` | Compatible base URL |
| `ALLINAGENT_MODEL` | `gpt-4o-mini` | Model name |

## Architecture

```
allinagent/
  cli.py       argparse + REPL
  agent.py     tool-calling loop
  tools.py     sandboxed workspace tools
  config.py    env / defaults
  prompts.py   system prompt
```

The agent sends your message + conversation history to the model with a fixed set of tools. The model returns either a final answer or tool calls; results are fed back until it finishes or hits `--max-steps`.

## Safety notes

- Paths are resolved under the workspace; path traversal is rejected.
- `write_file` and `run_shell` are off by default.
- Shell runs with `cwd=workspace` and a simple timeout; still treat it as powerful.
- Prefer `--dry-run` when exploring unfamiliar repos.

## Roadmap ideas

- Persistent session memory / project memory file
- Git-aware tools (status, diff, commit draft)
- Streaming output
- MCP / external tool plugins

## License

MIT
