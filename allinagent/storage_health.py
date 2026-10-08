"""Safe storage health checks for ALLINAGENT v1.5.0.

Reports disk free space and large workspace files. It never scans or deletes
Windows system directories and never performs automatic deletion.
"""
from __future__ import annotations
from pathlib import Path
import shutil
from dataclasses import dataclass

PROTECTED_WINDOWS_DIRS = {
    "system32", "syswow64", "winsxs", "boot", "servicing", "systemapps",
}

@dataclass(frozen=True)
class StorageSnapshot:
    root: Path
    total_bytes: int
    free_bytes: int
    used_bytes: int

    @property
    def free_percent(self) -> float:
        return (self.free_bytes / self.total_bytes * 100.0) if self.total_bytes else 0.0

    def summary(self) -> str:
        gb = 1024 ** 3
        return ("ALLINAGENT STORAGE HEALTH\n\n"
                f"Drive: {self.root}\n"
                f"Free: {self.free_bytes / gb:.2f} GB ({self.free_percent:.1f}%)\n"
                f"Used: {self.used_bytes / gb:.2f} GB\n"
                f"Total: {self.total_bytes / gb:.2f} GB\n\n"
                "Policy: inspection only; no automatic deletion.")

def snapshot(path: Path) -> StorageSnapshot:
    usage = shutil.disk_usage(path)
    return StorageSnapshot(Path(path), usage.total, usage.free, usage.used)

def large_files(workspace: Path, limit: int = 25) -> list[tuple[int, Path]]:
    results: list[tuple[int, Path]] = []
    ignored = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", "bin", "obj"}
    for p in workspace.rglob("*"):
        if not p.is_file() or any(part in ignored for part in p.relative_to(workspace).parts):
            continue
        try:
            results.append((p.stat().st_size, p))
        except OSError:
            continue
    return sorted(results, key=lambda x: -x[0])[:limit]

def daily_check(workspace: Path) -> str:
    s = snapshot(workspace)
    lines = [s.summary(), "", "Largest workspace files:"]
    for size, path in large_files(workspace):
        lines.append(f"- {size / 1024 / 1024:.2f} MB  {path.relative_to(workspace)}")
    if s.free_percent < 10:
        lines += ["", "WARNING: free space is below 10%."]
    elif s.free_percent < 20:
        lines += ["", "NOTICE: free space is below 20%."]
    else:
        lines += ["", "Storage status: HEALTHY."]
    return "\n".join(lines)
