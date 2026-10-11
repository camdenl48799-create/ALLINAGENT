"""Portable, versioned export/import for ALLINAGENT workspace JSON."""
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
from ..backup import create_backup

FORMAT_VERSION = 1
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
MEMORY_FILE = ".allinagent-memory.json"
PROJECT_FILE = ".allinagent/project.json"
_ALLOWED_FILES = {MEMORY_FILE, PROJECT_FILE}
_MANIFEST = "manifest.json"


def _read_workspace(workspace: Path, include_memory: bool, include_project: bool) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    requested = []
    if include_memory:
        requested.append(MEMORY_FILE)
    if include_project:
        requested.append(PROJECT_FILE)
    total = 0
    for relative in requested:
        path = workspace / relative
        if not path.is_file():
            continue
        raw = path.read_bytes()
        total += len(raw)
        if total > MAX_PACKAGE_BYTES:
            raise ValueError("Workspace export exceeds the supported size limit.")
        parsed = json.loads(raw.decode("utf-8"))
        if relative == MEMORY_FILE and (not isinstance(parsed, list) or not all(isinstance(x, dict) for x in parsed)):
            raise ValueError("Conversation memory has an invalid schema.")
        if relative == PROJECT_FILE and not isinstance(parsed, dict):
            raise ValueError("Project metadata has an invalid schema.")
        files[relative] = raw
    return files


def export_workspace(workspace: Path, output_path: Path, *, include_memory: bool = True, include_project: bool = True) -> dict:
    """Write a ZIP package containing only supported memory/project JSON."""
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"Workspace does not exist: {workspace}")
    files = _read_workspace(workspace, include_memory, include_project)
    manifest = {
        "format_version": FORMAT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": {
            name: {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
            for name, raw in files.items()
        },
    }
    output_path = Path(output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".allinagent-export-", suffix=".tmp", dir=output_path.parent)
    os.close(fd)
    temporary = Path(temp_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(_MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
            for name, raw in files.items():
                archive.writestr(name, raw)
        if temporary.stat().st_size > MAX_PACKAGE_BYTES:
            raise ValueError("Export package exceeds the supported size limit.")
        with zipfile.ZipFile(temporary, "r") as archive:
            if archive.testzip() is not None:
                raise ValueError("Export package failed ZIP integrity verification.")
        _inspect(temporary)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(output_path), "files": sorted(files), "file_count": len(files)}


def _inspect(package_path: Path) -> tuple[dict, dict[str, Any]]:
    package_path = Path(package_path)
    if not package_path.is_file():
        raise FileNotFoundError(f"Package not found: {package_path}")
    if package_path.stat().st_size > MAX_PACKAGE_BYTES:
        raise ValueError("Import package exceeds the supported size limit.")
    try:
        with zipfile.ZipFile(package_path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValueError("Package contains duplicate paths.")
            if _MANIFEST not in names or any(name not in _ALLOWED_FILES | {_MANIFEST} for name in names):
                raise ValueError("Package contains unsupported paths.")
            if sum(info.file_size for info in infos) > MAX_PACKAGE_BYTES:
                raise ValueError("Package contents exceed the supported size limit.")
            manifest = json.loads(archive.read(_MANIFEST).decode("utf-8"))
            if not isinstance(manifest, dict) or manifest.get("format_version") != FORMAT_VERSION:
                raise ValueError("Unsupported or malformed package manifest.")
            files_meta = manifest.get("files")
            if not isinstance(files_meta, dict) or set(files_meta) != set(names) - {_MANIFEST}:
                raise ValueError("Package manifest does not match its files.")
            payloads = {}
            for name, meta in files_meta.items():
                if not isinstance(meta, dict):
                    raise ValueError("Invalid file manifest entry.")
                raw = archive.read(name)
                if len(raw) != meta.get("size_bytes") or hashlib.sha256(raw).hexdigest() != meta.get("sha256"):
                    raise ValueError(f"Integrity check failed for {name}.")
                parsed = json.loads(raw.decode("utf-8"))
                if name == MEMORY_FILE and (not isinstance(parsed, list) or not all(isinstance(x, dict) for x in parsed)):
                    raise ValueError("Invalid conversation memory schema.")
                if name == PROJECT_FILE and not isinstance(parsed, dict):
                    raise ValueError("Invalid project metadata schema.")
                payloads[name] = parsed
            return manifest, payloads
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("Package is corrupt or malformed.") from exc


def inspect_package(package_path: Path) -> dict:
    """Validate a package without changing local files."""
    manifest, payloads = _inspect(package_path)
    return {
        "valid": True,
        "format_version": manifest["format_version"],
        "created_at": manifest.get("created_at"),
        "files": sorted(payloads),
        "record_count": sum(len(value) if isinstance(value, (list, dict)) else 0 for value in payloads.values()),
    }


def _merge_memory(existing: list[dict], incoming: list[dict]) -> list[dict]:
    merged = list(existing)
    seen = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in existing}
    for item in incoming:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged[-1000:]


def import_workspace(workspace: Path, package_path: Path, *, conflict: str = "preserve") -> dict:
    """Validate the entire package before writing any supported workspace file."""
    if conflict not in {"preserve", "replace"}:
        raise ValueError("conflict must be 'preserve' or 'replace'.")
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"Workspace does not exist: {workspace}")
    manifest, incoming = _inspect(package_path)
    planned: dict[str, Any] = {}
    conflicts: list[str] = []
    imported_counts: dict[str, int] = {}
    for relative, new_data in incoming.items():
        destination = workspace / relative
        current = None
        if destination.is_file():
            current = json.loads(destination.read_text(encoding="utf-8"))
        if current is not None and current != new_data:
            conflicts.append(relative)
        if conflict == "replace" or current is None:
            planned[relative] = new_data
            imported_counts[relative] = len(new_data) if isinstance(new_data, (list, dict)) else 0
        elif relative == MEMORY_FILE and isinstance(current, list) and isinstance(new_data, list):
            merged = _merge_memory(current, new_data)
            planned[relative] = merged
            imported_counts[relative] = max(0, len(merged) - len(current))
        elif relative == PROJECT_FILE and isinstance(current, dict) and isinstance(new_data, dict):
            merged = dict(new_data)
            merged.update(current)
            planned[relative] = merged
            imported_counts[relative] = sum(1 for key in new_data if key not in current)
        else:
            planned[relative] = current
            imported_counts[relative] = 0
    # Validate every destination before creating a checkpoint or writing files.
    for relative in planned:
        destination = workspace / relative
        if destination.exists() and not destination.is_file():
            raise ValueError(f"Import destination is not a file: {relative}")
    if planned and any((workspace / relative).is_file() for relative in planned):
        create_backup(workspace)
    for relative, data in planned.items():
        atomic_write_json(workspace / relative, data)
    return {
        "imported": imported_counts,
        "conflicts": sorted(conflicts),
        "conflict_policy": conflict,
        "source_unchanged": True,
        "package_created_at": manifest.get("created_at"),
    }
