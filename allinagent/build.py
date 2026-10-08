"""Project build and Windows executable packaging for ALLINAGENT.

Runs build commands through PowerShell without spawning a visible terminal window.
The build log is returned to the caller so the CLI/agent can display every command.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

MAX_OUTPUT = 30_000
DEFAULT_TIMEOUT = 120


class BuildError(RuntimeError):
    """Raised for invalid or unsupported build requests."""


class WindowsBuilder:
    """Detect, build, and validate Windows executable projects."""

    def __init__(self, workspace: Path, allow_shell: bool = False, dry_run: bool = False) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.allow_shell = bool(allow_shell)
        self.dry_run = bool(dry_run)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _safe(self, value: str | Path) -> Path:
        raw = Path(value).expanduser()
        target = ((self.workspace / raw) if not raw.is_absolute() else raw).resolve()
        try:
            target.relative_to(self.workspace)
        except ValueError as exc:
            raise BuildError(f"Path escapes workspace: {value}") from exc
        return target

    @staticmethod
    def _ps_quote(value: str | Path) -> str:
        """Quote a path as a literal PowerShell string."""
        return "'" + str(value).replace("'", "''") + "'"

    def _run_powershell(self, command: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str]:
        if os.name != "nt":
            raise BuildError("Windows EXE building requires Windows/PowerShell.")
        if not shutil.which("powershell.exe"):
            raise BuildError("Windows PowerShell (powershell.exe) was not found.")
        shown = command.strip()
        if not shown:
            raise BuildError("Build command is empty.")
        if self.dry_run:
            return 0, f"$ {shown}\n[DRY RUN] command not executed."
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", shown],
                cwd=self.workspace, text=True, capture_output=True,
                timeout=timeout, env=os.environ.copy(), creationflags=creationflags,
            )
        except subprocess.TimeoutExpired:
            return 124, f"$ {shown}\nTIMEOUT after {timeout}s"
        except OSError as exc:
            raise BuildError(f"Could not start PowerShell: {exc}") from exc
        output = proc.stdout or ""
        if proc.stderr:
            output += ("\n" if output else "") + "[stderr]\n" + proc.stderr
        if len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT] + "\n... [output truncated]"
        return proc.returncode, f"$ {shown}\n{output}".rstrip()

    @staticmethod
    def _has_any(root: Path, names: Iterable[str]) -> Path | None:
        for name in names:
            found = root / name
            if found.is_file():
                return found
        return None

    def detect(self) -> dict:
        csproj = next(iter(self.workspace.glob("*.csproj")), None)
        if csproj:
            return {"type": "dotnet", "entry": csproj.relative_to(self.workspace).as_posix()}
        pyproject = self.workspace / "pyproject.toml"
        if pyproject.exists():
            main = self._has_any(self.workspace, ("main.py", "__main__.py", "app.py"))
            return {"type": "python", "entry": main.relative_to(self.workspace).as_posix() if main else None}
        main = self._has_any(self.workspace, ("main.py", "app.py", "__main__.py"))
        if main:
            return {"type": "python", "entry": main.relative_to(self.workspace).as_posix()}
        package = self.workspace / "package.json"
        if package.exists():
            return {"type": "node", "entry": "package.json"}
        return {"type": "unknown", "entry": None}

    def _find_exes(self, before: set[Path], root: Path | None = None) -> list[Path]:
        found = []
        for p in (root or self.workspace).rglob("*.exe"):
            if any(part in {".git", ".venv", "venv", "node_modules", "__pycache__"} for part in p.parts):
                continue
            if p not in before and p.is_file():
                found.append(p)
        return sorted(found, key=lambda p: p.stat().st_mtime_ns, reverse=True)

    def build(self, project: str | None = None, entry: str | None = None,
              output: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
        if not self.allow_shell:
            return "BUILD DENIED: pass --allow-shell to enable build execution."
        if self.dry_run:
            return "BUILD BLOCKED: --dry-run is active; no build executed."
        detection = self.detect()
        kind = detection["type"]
        project_path = self._safe(project) if project else None
        entry_path = self._safe(entry) if entry else None
        before = set(self.workspace.rglob("*.exe"))

        if kind == "dotnet":
            csproj = project_path or self._safe(detection["entry"])
            rel = csproj.relative_to(self.workspace).as_posix()
            command = (
                f"dotnet publish {self._ps_quote(rel)} -c Release -r win-x64 "
                f"--self-contained true -p:PublishSingleFile=true"
            )
            if output:
                out = self._safe(output)
                command += f" -o {self._ps_quote(out.relative_to(self.workspace).as_posix())}"
        elif kind == "python":
            main = entry_path or (self._safe(detection["entry"]) if detection["entry"] else None)
            if not main:
                return "BUILD ERROR: Python project detected but no entry file was found. Specify entry=main.py."
            rel = main.relative_to(self.workspace).as_posix()
            command = f"python -m PyInstaller --noconfirm --clean --onefile --windowed {self._ps_quote(rel)}"
        elif kind == "node":
            return ("BUILD UNSUPPORTED: package.json was detected, but Node.js projects need "
                    "an explicit Windows packaging tool/configuration (for example an existing "
                    "electron-builder or other EXE-capable setup).")
        else:
            return ("BUILD UNSUPPORTED: could not detect a supported Windows executable project. "
                    "Supported automatic builders currently include .NET and Python/PyInstaller.")

        code, log = self._run_powershell(command, timeout)
        if code != 0:
            return f"BUILD FAILED\n{log}\n\nExit code: {code}"

        out_dir = self._safe(output) if output else None
        exes = self._find_exes(before, out_dir)
        if not exes and out_dir is not None:
            exes = self._find_exes(set(), out_dir)
        if not exes:
            reason = (f"No .exe file was found in the output directory: {out_dir}."
                      if output else "No new .exe file was produced by the build.")
            return f"BUILD FAILED\n{log}\n\n{reason}"

        exe = exes[0]
        size = exe.stat().st_size
        if size <= 0:
            return f"BUILD FAILED\n{log}\n\nEXE validation failed: {exe} is empty."

        check = f"(Get-Item -LiteralPath {self._ps_quote(exe.relative_to(self.workspace).as_posix())}).Length"
        check_code, check_log = self._run_powershell(check, timeout=30)
        if check_code != 0:
            return f"BUILD FAILED\n{log}\n\nEXE validation failed\n{check_log}"

        return (
            f"BUILD COMPLETE\n{log}\n\n"
            f"✓ EXE created: {exe}\n✓ EXE size: {size:,} bytes\n"
            "✓ EXE file validation passed\n"
            "NOTE: the executable was not automatically launched."
        )
