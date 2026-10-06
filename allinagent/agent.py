from pathlib import Path
from .tools import WorkspaceTools

class Agent:
    def __init__(self, workspace: Path, dry_run: bool = False):
        self.workspace = workspace
        self.tools = WorkspaceTools(workspace, dry_run=dry_run)

    def run(self, prompt: str) -> str:
        text = prompt.lower().strip()
        if text.startswith("analyze") or "analyze this project" in text:
            return self.tools.project_summary()
        if text.startswith("cleanup") or "free space" in text or "free up space" in text:
            return self.tools.storage_report()
        return (
            "ALLINAGENT v0.1 received your task.\n"
            "The safe local tool layer is ready; the model adapter will be added next.\n"
            f"Workspace: {self.workspace}\nTask: {prompt}"
        )
