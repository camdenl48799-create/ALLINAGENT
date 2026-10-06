"""Offline local brain for ALLINAGENT."""
from __future__ import annotations
import re
from .tools import WorkspaceTools

class LocalBrain:
    def __init__(self, tools: WorkspaceTools):
        self.tools = tools

    def can_handle(self, prompt: str) -> bool:
        text = prompt.lower().strip()
        patterns = [r"\bwho are you\b", r"\bwhat are you\b", r"\bhelp\b", r"\banaly[sz]e\b", r"\bproject\b.*\b(summary|structure)\b", r"\bfree (up )?space\b", r"\bclean( up)?\b.*\bspace\b", r"\blist\b.*\b(files|directory|folder)\b", r"\bread\b.*\bfile\b", r"\b(find|search)\b"]
        return any(re.search(p, text) for p in patterns)

    def run(self, prompt: str) -> str:
        text = prompt.lower().strip()
        if re.search(r"\b(who|what) are you\b", text):
            return "I’m ALLINAGENT — an independent, local-first AI coding agent.\nMy local brain and tools run on your machine. External models are optional fuel."
        if text in {"help", "--help"} or "what can you do" in text:
            return "ALLINAGENT local mode\n  analyze project   Inspect the workspace\n  list files        Show workspace files\n  free up space     Report large files (no deletion)\n  read file <path>  Read a text file safely\n  find <text>       Search workspace text\n\nWrites and shell commands require explicit permissions."
        if "free space" in text or "free up space" in text or ("clean" in text and "space" in text):
            return self.tools.storage_report()
        if text.startswith("analyze") or "project structure" in text or "project summary" in text:
            return self.tools.project_summary()
        if text.startswith("list"):
            return self.tools.list_dir(".")
        match = re.search(r"read (?:file )?['\"]?([^'\"]+)['\"]?$", prompt.strip(), re.I)
        if match:
            return self.tools.read_file(match.group(1))
        match = re.search(r"(?:find|search)(?: for)? ['\"]?(.+?)['\"]?$", prompt.strip(), re.I)
        if match:
            return self.tools.search_text(match.group(1))
        return "ALLINAGENT local brain cannot complete that task yet without an external reasoning model. No request was sent off-machine."
