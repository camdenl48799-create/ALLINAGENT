from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import OpenAI

from .config import Config
from .prompts import SYSTEM_PROMPT
from .tools import WorkspaceTools


class Agent:
    def __init__(
        self,
        workspace: Path,
        config: Config,
        *,
        dry_run: bool = False,
        allow_write: bool = False,
        allow_shell: bool = False,
        verbose: bool = False,
    ):
        self.workspace = workspace.resolve()
        self.config = config
        self.verbose = verbose
        self.tools = WorkspaceTools(
            self.workspace,
            dry_run=dry_run,
            allow_write=allow_write,
            allow_shell=allow_shell,
        )
        self.client = OpenAI(
            api_key=config.api_key or "dummy",
            base_url=config.base_url,
        )
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    def _chat(self, messages: list[dict[str, Any]]) -> Any:
        return self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=self.tools.openai_tools(),
            tool_choice="auto",
        )

    def run(self, prompt: str) -> str:
        if not self.config.api_key:
            return (
                "No API key set. Export ALLINAGENT_API_KEY or OPENAI_API_KEY.\n"
                "For local Ollama: ALLINAGENT_BASE_URL=http://127.0.0.1:11434/v1 "
                "ALLINAGENT_API_KEY=ollama ALLINAGENT_MODEL=llama3.2"
            )

        self.messages.append({"role": "user", "content": prompt})
        steps = 0

        while steps < self.config.max_steps:
            steps += 1
            try:
                resp = self._chat(self.messages)
            except Exception as e:  # noqa: BLE001
                return f"API error: {type(e).__name__}: {e}"

            choice = resp.choices[0]
            msg = choice.message
            tool_calls = msg.tool_calls or []

            assistant_entry: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
            if tool_calls:
                assistant_entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in tool_calls
                ]
            self.messages.append(assistant_entry)

            if not tool_calls:
                final = (msg.content or "").strip()
                return final or "(empty model response)"

            for tc in tool_calls:
                name = tc.function.name
                args = tc.function.arguments or "{}"
                if self.verbose:
                    print(f"  → tool {name}({args[:120]}{'…' if len(args) > 120 else ''})")
                result = self.tools.dispatch(name, args)
                if self.verbose and len(result) > 200:
                    print(f"  ← {result[:200]}…")
                elif self.verbose:
                    print(f"  ← {result}")
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        return (
            f"Stopped after {self.config.max_steps} tool steps. "
            "Raise --max-steps or narrow the task."
        )

    def reset_conversation(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
