# ALLINAGENT

**Its own local-first AI coding agent.**

ALLINAGENT is not a ChatGPT wrapper. It is an independent agent that:

- Runs **on your machine**, in **your project folder**
- Owns a **local brain** that works **with zero API key**
- Optionally uses any OpenAI-compatible model (including ones you host) as a *reasoning accelerator* — not as its identity

```text
You → ALLINAGENT (local brain + tools)
              ↘ optional external model (only if you want)
```

## Why this exists

Most “AI coding agents” are thin clients around someone else’s chat product. ALLINAGENT flips that: the agent, tools, and offline behavior are first-class. External models are optional fuel, not the product.

## Features

| Capability | Offline (local brain) | With optional LLM |
|------------|----------------------|-------------------|
| Identity / help | ✓ | ✓ |
| Project analyze / list / read / search | ✓ | ✓ |
| Storage / cleanup report | ✓ | ✓ |
| Multi-step coding plans | limited | ✓ |
| Write / shell | gated flags | gated flags |

## Install

```bash
pip install -e .                 # local brain only — no extra deps
pip install -e ".[llm]"          # + openai SDK for external / local models
```

Python 3.10+.

## Quick start (no API key)

```bash
cd /path/to/your/project
allinagent "who are you"
allinagent "analyze this project"
allinagent "search TODO"
allinagent "storage report"
allinagent -i                    # REPL
allinagent --local "list files"  # force local brain
```

## Optional model (still ALLINAGENT)

```bash
export ALLINAGENT_API_KEY=sk-...
# export ALLINAGENT_BASE_URL=https://api.openai.com/v1
# export ALLINAGENT_MODEL=gpt-4o-mini
allinagent --llm "refactor the CLI help text"
```

**Your own model (Ollama):**

```bash
export ALLINAGENT_BASE_URL=http://127.0.0.1:11434/v1
export ALLINAGENT_API_KEY=ollama
export ALLINAGENT_MODEL=llama3.2
pip install -e ".[llm]"
allinagent --llm "explain the entry points"
```

If the external model fails, ALLINAGENT falls back to its local brain instead of dying.

## CLI

```
allinagent [options] [prompt...]

  --workspace PATH   Project root (default: .)
  --interactive, -i  REPL
  --local            Force local brain (no external model)
  --llm              Prefer external model when configured
  --dry-run          No writes / shell
  --allow-write      Enable write_file
  --allow-shell      Enable run_shell
  --model NAME
  --base-url URL
  --max-steps N
  --verbose, -v
```

In the REPL: `status`, `reset`, `exit`.

## Architecture

```
allinagent/
  local_brain.py   ALLINAGENT's own offline reasoning
  agent.py         Routes local brain vs optional LLM tool loop
  tools.py         Sandboxed workspace tools (the body)
  prompts.py       Identity when an external model is used
  config.py        Env / defaults
  cli.py           CLI + REPL
```

**Default path:** local brain if it can handle the task or no key is set.  
**Opt-in path:** `--llm` + API key / local server for harder multi-step work.

## Safety

- Paths cannot escape the workspace
- Writes and shell are **off** unless you pass flags
- `--dry-run` disables mutations even if those flags are set
- Local brain never sends your code anywhere

## License

MIT
