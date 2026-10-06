from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .config import Config
from .local_brain import LocalBrain
from .prompts import SYSTEM_PROMPT
from .tools import WorkspaceTools


class Agent:
    """ALLINAGENT: local brain first, optional external model second."""

    def __init__(
        self,
        workspace: Path,
        config: Config,
        *,
        dry_run: bool = False,
        allow_write: bool = False,
        allow_shell: bool = False,
        verbose: bool = False,
        force_local: bool = False,
        force_llm: bool = False,
    ):
        self.workspace = workspace.resolve()
        self.config = config
        self.verbose = verbose
        self.force_local = force_local
        self.force_llm = force_llm
        self.tools = WorkspaceTools(
            self.workspace,
            dry_run=dry_run,
            allow_write=allow_write,
            allow_shell=allow_shell,
        )
        self.local = LocalBrain(self.tools)
        self._client = None
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    @property
    def has_llm(self) -> bool:
        return bool(self.config.api_key) and not self.force_local

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "openai package not installed. `pip install openai` "
                "or use local mode (no key required)."
            ) from e
        self._client = OpenAI(
            api_key=self.config.api_key or "dummy",
            base_url=self.config.base_url,
        )
        return self._client

    def run(self, prompt: str) -> str:
        prompt = (prompt or "").strip()
        if not prompt:
            return self.local.think("help")

        # Prefer ALLINAGENT's own brain when it can handle the task
        use_local = self.force_local or (
            not self.force_llm and (not self.has_llm or self.local.can_handle(prompt))
        )
        if use_local and not self.force_llm:
            if self.verbose:
                print("  → ALLINAGENT local brain")
            return self.local.think(prompt)

        if not self.has_llm:
            if self.verbose:
                print("  → ALLINAGENT local brain (no API key)")
            return self.local.think(prompt)

        return self._run_llm(prompt)

    def _run_llm(self, prompt: str) -> str:
        self.messages.append({"role": "user", "content": prompt})
        steps = 0
        client = self._get_client()

        while steps < self.config.max_steps:
            steps += 1
            try:
                resp = client.chat.completions.create(
                    model=self.config.model,
                    messages=self.messages,
                    tools=self.tools.openai_tools(),
                    tool_choice="auto",
                )
            except Exception as e:  # noqa: BLE001
                # Fall back to local brain so ALLINAGENT still answers
                if self.verbose:
                    print(f"  → LLM failed ({e}); local brain")
                self.messages.pop()  # remove user msg to avoid double-append on retry paths
                return (
                    f"[ALLINAGENT] External model unavailable ({type(e).__name__}: {e}).\n"
                    f"Falling back to local brain:\n\n{self.local.think(prompt)}"
                )

            choice = resp.choices[0]
            msg = choice.message
            tool_calls = msg.tool_calls or []

            assistant_entry: dict[str, Any] = {
                "role": "assistant",
                "content": msg.content or "",
            }
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
                if self.verbose:
                    preview = result if len(result) <= 200 else result[:200] + "…"
                    print(f"  ← {preview}")
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        return (
            f"ALLINAGENT stopped after {self.config.max_steps} tool steps. "
            "Raise --max-steps or narrow the task."
        )

    def reset_conversation(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def status_line(self) -> str:
        mode = "local-brain" if not self.has_llm else f"hybrid ({self.config.model})"
        if self.force_local:
            mode = "local-brain (forced)"
        if self.force_llm and self.has_llm:
            mode = f"llm ({self.config.model})"
        return f"ALLINAGENT v{__version__}  mode={mode}  workspace={self.workspace}"
