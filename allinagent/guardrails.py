"""Safety guardrails for ALLINAGENT operations.

Classifies destructive operations and requires explicit confirmation
for dangerous actions. Prevents bulk deletes, project removal,
and overwriting important configuration files.
"""
from __future__ import annotations

import re
from enum import Enum

from .tools import WorkspaceTools


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


DANGEROUS_COMMANDS = {
    "rm -rf", "rmdir", "del", "format", "mkfs", "dd of=/dev/",
    "shutdown", "reboot", "halt", "poweroff",
    "chmod 777", "chown root",
    "curl", "wget", "scp", "rsync",
    "docker", "kubernetes", "kubectl",
    "sudo", "su ",
}

PROTECTED_FILES = {
    ".allinagent.toml", "pyproject.toml", "setup.py", "setup.cfg",
    "requirements.txt", "package.json", "Cargo.toml", "go.mod",
    ".env", ".env.local", ".env.production", ".env.example",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".git/config", ".gitignore", "Makefile", "CMakeLists.txt",
    "tsconfig.json", "next.config.js", "next.config.mjs",
    "vite.config.js", "vite.config.ts", "webpack.config.js",
    ".allinagent/project.json", ".allinagent-memory.json",
}

PROTECTED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".allinagent", ".next", "dist", "build",
}


class Guardrails:
    """Evaluate operations for safety before execution."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    def classify_delete(self, path: str) -> tuple[RiskLevel, str]:
        """Classify the risk level of deleting a path."""
        try:
            full = self.tools._safe_path(path)
        except Exception:
            return (RiskLevel.CRITICAL, "path escapes workspace sandbox")

        if not full.exists():
            return (RiskLevel.LOW, "path does not exist")

        rel = self.tools._display(full)

        # Never allow deleting workspace root
        if rel == "." or rel == "":
            return (RiskLevel.CRITICAL, "cannot delete the workspace root")

        # Check protected directories
        parts = full.relative_to(self.tools.workspace).parts
        for part in parts:
            if part in PROTECTED_DIRS:
                return (RiskLevel.CRITICAL, f"cannot delete protected directory: {part}")

        # Check protected files
        if full.name in PROTECTED_FILES or rel in PROTECTED_FILES:
            return (RiskLevel.HIGH, f"protected configuration file: {full.name}")

        # Count files that would be deleted
        if full.is_dir():
            try:
                count = sum(1 for _ in full.rglob("*") if _.is_file())
            except OSError:
                count = 0
            if count > 50:
                return (RiskLevel.HIGH, f"directory contains {count} files")
            elif count > 10:
                return (RiskLevel.MODERATE, f"directory contains {count} files")
            elif count > 0:
                return (RiskLevel.LOW, f"directory contains {count} files")

        return (RiskLevel.LOW, "single file")

    def classify_shell(self, command: str) -> tuple[RiskLevel, str]:
        """Classify the risk level of a shell command."""
        cmd = command.strip().lower()

        for dangerous in DANGEROUS_COMMANDS:
            if dangerous in cmd:
                if any(word in cmd for word in ("rm -rf /", "rm -rf ~", "mkfs", "dd of=/dev/", "shutdown", "reboot")):
                    return (RiskLevel.CRITICAL, f"potentially destructive command detected")
                return (RiskLevel.HIGH, f"potentially dangerous command pattern: {dangerous}")

        if "rm " in cmd or "del " in cmd:
            if "-rf" in cmd or "-r" in cmd:
                return (RiskLevel.HIGH, "recursive delete detected")
            return (RiskLevel.MODERATE, "file deletion detected")

        if ">" in cmd and "/dev/" in cmd:
            return (RiskLevel.HIGH, "writing to device files detected")

        return (RiskLevel.SAFE, "command appears safe")

    def classify_overwrite(self, path: str) -> tuple[RiskLevel, str]:
        """Classify the risk of overwriting a file."""
        try:
            full = self.tools._safe_path(path)
        except Exception:
            return (RiskLevel.CRITICAL, "path escapes workspace sandbox")

        if not full.exists():
            return (RiskLevel.SAFE, "new file, no overwrite")

        if full.name in PROTECTED_FILES:
            return (RiskLevel.HIGH, f"overwriting protected file: {full.name}")

        return (RiskLevel.LOW, "overwriting existing file")

    def requires_confirmation(self, risk: RiskLevel) -> bool:
        """Return True if a risk level requires user confirmation."""
        return risk in (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL)

    def explain_risk(self, risk: RiskLevel, detail: str) -> str:
        """Return a user-facing risk explanation."""
        levels = {
            RiskLevel.SAFE: "SAFE",
            RiskLevel.LOW: "LOW RISK",
            RiskLevel.MODERATE: "MODERATE RISK — confirmation recommended",
            RiskLevel.HIGH: "HIGH RISK — confirmation required",
            RiskLevel.CRITICAL: "CRITICAL — operation blocked",
        }
        return f"{levels.get(risk, 'UNKNOWN')}: {detail}"
