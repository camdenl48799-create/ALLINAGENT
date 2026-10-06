from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tools import WorkspaceTools

from . import __identity__, __version__


class LocalBrain:
    """ALLINAGENT's own offline reasoning — no external model required.

    Handles identity, project inspection, search, and storage reports by
    chaining workspace tools directly. This is the default brain.
    """

    def __init__(self, tools: WorkspaceTools):
        self.tools = tools

    def can_handle(self, prompt: str) -> bool:
        text = prompt.lower().strip()
        if not text:
            return True
        identity = (
            "who are you",
            "what are you",
            "your name",
            "about yourself",
            "about allinagent",
            "help",
            "what can you do",
        )
        if any(k in text for k in identity):
            return True
        intents = (
            "analyze",
            "summary",
            "summarize",
            "project",
            "list files",
            "list dir",
            "show files",
            "tree",
            "cleanup",
            "free space",
            "free up",
            "storage",
            "largest",
            "disk",
            "search",
            "find",
            "grep",
            "look for",
            "read ",
            "open ",
            "show me",
            "what's in",
            "whats in",
        )
        return any(k in text for k in intents)

    def think(self, prompt: str) -> str:
        text = prompt.lower().strip()
        if not text or text in {"help", "?"}:
            return self._help()

        if any(
            k in text
            for k in (
                "who are you",
                "what are you",
                "your name",
                "about yourself",
                "about allinagent",
            )
        ):
            return self._identity()

        if any(k in text for k in ("cleanup", "free space", "free up", "storage", "largest", "disk")):
            report = self.tools.storage_report()
            return (
                "ALLINAGENT local storage scan complete.\n\n"
                f"{report}\n\n"
                "I do not delete anything unless you explicitly ask and enable writes. "
                "I am not a cloud chatbot — this report came from my own tools on your disk."
            )

        if any(k in text for k in ("analyze", "summary", "summarize", "project overview", "overview")):
            summary = self.tools.project_summary()
            root_listing = self.tools.list_dir(".")
            return (
                f"ALLINAGENT v{__version__} — local project analysis\n\n"
                f"{summary}\n\n"
                f"Root directory:\n{root_listing}\n\n"
                "This analysis was produced by ALLINAGENT's local brain and workspace tools, "
                "not by outsourcing your repo to a third-party chat product."
            )

        if any(k in text for k in ("list files", "list dir", "show files", "tree", "ls ")):
            path = self._extract_path(prompt) or "."
            return f"ALLINAGENT listing `{path}`:\n\n{self.tools.list_dir(path)}"

        if text.startswith("read ") or text.startswith("open ") or "show me" in text:
            path = self._extract_path(prompt)
            if path:
                return self.tools.read_file(path)
            return "Tell me which relative path to read, e.g. `read allinagent/agent.py`."

        if any(k in text for k in ("search", "find", "grep", "look for")):
            pattern = self._extract_search_pattern(prompt)
            if not pattern:
                return "What should I search for? Example: `search def main` or `find TODO`."
            hits = self.tools.search_text(pattern)
            return f"ALLINAGENT search for /{pattern}/:\n\n{hits}"

        # Soft fallback still stays local
        summary = self.tools.project_summary()
        return (
            f"ALLINAGENT local mode (no external model used for this turn).\n"
            f"Task: {prompt}\n\n"
            f"{summary}\n\n"
            "I handled this with my own tools. For deeper multi-step coding help, "
            "set an API key or point me at a local model (Ollama/LM Studio) — "
            "I remain ALLINAGENT either way, not a rebranded chat UI."
        )

    def _identity(self) -> str:
        return (
            f"I am ALLINAGENT v{__version__}.\n\n"
            f"{__identity__}\n\n"
            "What I am:\n"
            "- A local-first coding agent that lives in your project folder\n"
            "- Owner of my own tool layer (list, read, search, storage, optional write/shell)\n"
            "- Able to run fully offline via my local brain\n"
            "- Optional: I can use any OpenAI-compatible model as a reasoning accelerator, "
            "  including models you host yourself\n\n"
            "What I am not:\n"
            "- Not ChatGPT, not Claude, not a white-label wrapper\n"
            "- Not a cloud product that requires your code to leave the machine\n\n"
            "Try: analyze this project | search TODO | storage report | help"
        )

    def _help(self) -> str:
        return (
            f"ALLINAGENT v{__version__} — commands (local brain)\n\n"
            "  analyze this project     Project map via local tools\n"
            "  storage / cleanup        Largest files report (no deletes)\n"
            "  list files [path]        Directory listing\n"
            "  search <pattern>         Regex search in the workspace\n"
            "  read <path>              Read a file\n"
            "  who are you              Identity\n\n"
            "Flags: --dry-run  --allow-write  --allow-shell  -i  --verbose\n"
            "Optional LLM: set ALLINAGENT_API_KEY / ALLINAGENT_BASE_URL / ALLINAGENT_MODEL\n"
            "Local models work (Ollama, LM Studio). I stay ALLINAGENT either way."
        )

    def _extract_path(self, prompt: str) -> str | None:
        # read path/to/file.py  |  open src/main.ts
        m = re.search(
            r"(?:read|open|show(?:\s+me)?|list(?:\s+(?:dir|files)?)|ls)\s+([\w./\\-]+)",
            prompt,
            re.I,
        )
        if m:
            return m.group(1).strip("`'\"")
        # bare path-looking token
        m = re.search(r"([\w.-]+(?:/[\w.-]+)+\.[\w]+)", prompt)
        if m:
            return m.group(1)
        return None

    def _extract_search_pattern(self, prompt: str) -> str | None:
        m = re.search(
            r"(?:search|find|grep|look for)\s+(?:for\s+)?(.+)$",
            prompt,
            re.I,
        )
        if not m:
            return None
        pat = m.group(1).strip().strip("`'\"")
        # strip trailing "in path" noise lightly
        pat = re.sub(r"\s+in\s+\S+$", "", pat).strip()
        return pat or None
