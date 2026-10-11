"""Versioned, integrity-checked local backups for ALLINAGENT."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .._persistence import atomic_write_json

FORMAT_VERSION = 1
MAX_BACKUP_BYTES = 10 * 1024 * 1024
MEMORY_FILE = ".allinagent-memory.json"
PROJECT_FILE = ".allinagent/project.json"
_ALLOWED_FILES = {MEMORY_FILE, PROJECT_FILE}
_MANIFEST = "manifest.json"


def _default_root() -> Path:
    return Path.home() / ".allinagent" / "backups"


def _record_count(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return len(data)
    return 0


def _workspace_files(workspace: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for relative in sorted(_ALLOWED_FILES):
        path = workspace / relative
        if path.is_file():
            raw = path.read_bytes()
            if len(raw) > MAX_BACKUP_BYTES:
                raise ValueError(f"Backup input is too large: {relative}")
            # Validate JSON before including it.
            data = json.loads(raw.decode("utf-8"))
            if relative == MEMORY_FILE and not isinstance(data, list):
                raise ValueError("Conversation memory must be a JSON list.")
            if relative == PROJECT_FILE and not isinstance(data, dict):
                raise ValueError("Project metadata must be a JSON object.")
            found[relative] = raw
    return found


def create_backup(workspace: Path, backup_root: Path | None = None) -> Path:
    """Create a verified ZIP backup of supported local memory files."""
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"Workspace does not exist: {workspace}")
    files = _workspace_files(workspace)
    root = Path(backup_root) if backup_root is not None else _default_root()
    root.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    manifest = {
        "format_version": FORMAT_VERSION,
        "created_at": now.isoformat(),
        "files": {
            name: {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
                "record_count": _record_count(json.loads(raw.decode("utf-8"))),
            }
            for name, raw in files.items()
        },
    }
    output = root / f"allinagent-backup-{now.strftime('%Y%m%dT%H%M%S%fZ')}.zip"
    fd, temp_name = tempfile.mkstemp(prefix=".backup-", suffix=".tmp", dir=root)
    os.close(fd)
    temporary = Path(temp_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(_MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
            for name, raw in files.items():
                archive.writestr(name, raw)
        if temporary.stat().st_size > MAX_BACKUP_BYTES:
            raise ValueError("Backup archive exceeds the supported size limit.")
        with zipfile.ZipFile(temporary, "r") as archive:
            if archive.testzip() is not None:
                raise ValueError("Backup archive failed ZIP integrity verification.")
        os.replace(temporary, output)
        return output
    finally:
        temporary.unlink(missing_ok=True)


def _read_verified(backup_path: Path) -> tuple[dict, dict[str, bytes]]:
    backup_path = Path(backup_path)
    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    if backup_path.stat().st_size > MAX_BACKUP_BYTES:
        raise ValueError("Backup archive exceeds the supported size limit.")
    try:
        with zipfile.ZipFile(backup_path, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Backup contains duplicate paths.")
            if _MANIFEST not in names or any(name not in _ALLOWED_FILES | {_MANIFEST} for name in names):
                raise ValueError("Backup contains unsupported paths.")
            if sum(info.file_size for info in archive.infolist()) > MAX_BACKUP_BYTES:
                raise ValueError("Backup contents exceed the supported size limit.")
            manifest = json.loads(archive.read(_MANIFEST).decode("utf-8"))
            if not isinstance(manifest, dict) or manifest.get("format_version") != FORMAT_VERSION:
                raise ValueError("Unsupported or malformed backup manifest.")
            file_manifest = manifest.get("files")
            if not isinstance(file_manifest, dict) or set(file_manifest) != set(names) - {_MANIFEST}:
                raise ValueError("Backup manifest does not match its files.")
            files: dict[str, bytes] = {}
            for name, metadata in file_manifest.items():
                if name not in _ALLOWED_FILES or not isinstance(metadata, dict):
                    raise ValueError("Invalid backup file entry.")
                raw = archive.read(name)
                if len(raw) != metadata.get("size_bytes"):
                    raise ValueError(f"Size mismatch for {name}.")
                if hashlib.sha256(raw).hexdigest() != metadata.get("sha256"):
                    raise ValueError(f"Integrity check failed for {name}.")
                parsed = json.loads(raw.decode("utf-8"))
                if name == MEMORY_FILE and (not isinstance(parsed, list) or not all(isinstance(x, dict) for x in parsed)):
                    raise ValueError("Invalid conversation memory schema.")
                if name == PROJECT_FILE and not isinstance(parsed, dict):
                    raise ValueError("Invalid project metadata schema.")
                if metadata.get("record_count") != _record_count(parsed):
                    raise ValueError(f"Record count mismatch for {name}.")
                files[name] = raw
            return manifest, files
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("Backup is corrupt or malformed.") from exc


def verify_backup(backup_path: Path) -> dict:
    """Validate a backup completely without modifying the workspace."""
    manifest, files = _read_verified(backup_path)
    return {
        "valid": True,
        "format_version": manifest["format_version"],
        "created_at": manifest.get("created_at"),
        "files": sorted(files),
        "file_count": len(files),
        "record_count": sum(_record_count(json.loads(raw.decode("utf-8"))) for raw in files.values()),
    }


def list_backups(backup_root: Path | None = None) -> list[dict]:
    root = Path(backup_root) if backup_root is not None else _default_root()
    if not root.exists():
        return []
    results = []
    for path in sorted(root.glob("allinagent-backup-*.zip")):
        try:
            details = verify_backup(path)
            results.append({"path": str(path), **details})
        except (OSError, ValueError):
            results.append({"path": str(path), "valid": False})
    return results


def restore_backup(workspace: Path, backup_path: Path, *, replace: bool = False) -> dict:
    """Restore validated JSON files; never replace differing files implicitly."""
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"Workspace does not exist: {workspace}")
    manifest, files = _read_verified(backup_path)
    conflicts = []
    for relative, raw in files.items():
        destination = workspace / relative
        if destination.is_file() and destination.read_bytes() != raw:
            conflicts.append(relative)
    if conflicts and not replace:
        raise FileExistsError("Restore would replace existing data: " + ", ".join(sorted(conflicts)))
    if any((workspace / name).exists() and not (workspace / name).is_file() for name in files):
        raise ValueError("Restore destination conflicts with an existing non-file path.")
    # Checkpoint current supported data before an explicitly requested replacement.
    if _workspace_files(workspace):
        create_backup(workspace)
    staged = []
    try:
        for relative, raw in files.items():
            destination = workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix=f".{destination.name}.restore-", suffix=".tmp", dir=destination.parent)
            temporary = Path(name)
            staged.append((temporary, destination))
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        for temporary, destination in staged:
            os.replace(temporary, destination)
    finally:
        for temporary, _destination in staged:
            temporary.unlink(missing_ok=True)
    return {
        "restored": sorted(files),
        "conflicts_replaced": sorted(conflicts),
        "created_at": manifest.get("created_at"),
    }
