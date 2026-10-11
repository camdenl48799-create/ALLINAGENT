# ALLINAGENT v1.6.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve local memory durability, add verified backup/restore and safe export/import, and add a separately runnable browser workspace without breaking the CLI.

**Architecture:** Keep the Python CLI as the local-first core. Add standard-library backup and transfer modules with explicit CLI commands. Add a static HTML/CSS/JS workspace under `web/`, independently testable and honest about its browser-local storage boundary.

**Tech Stack:** Python 3.10+, setuptools, pytest, standard library, vanilla HTML/CSS/JavaScript; no required paid services or third-party web dependencies.

**Spec:** `docs/superpowers/specs/2026-10-10-allinagent-ecosystem-design.md`

## Global Constraints
- Preserve existing CLI behavior and compatibility with current memory/project JSON.
- External model use remains opt-in; do not claim a first-party One- model is already available.
- Keep local data local unless the user explicitly exports it.
- Never silently discard save failures, overwrite newer data without confirmation, or delete source data during transfer.
- Preserve malformed data for diagnosis; do not claim recovery if no valid copy exists.
- Validate imports/backups completely before live writes; do not expose secrets in logs or browser code.
- No paid server, API key, cloud sync, or account system is assumed.

## Review Focus
- Malformed/truncated memory: preserve original bytes and report an issue, not an empty success.
- Failed writes/replacements: preserve the last valid file and surface failure.
- Stale restore/conflicts: no silent overwrite; report conflict details.
- Corrupt/oversized transfer archives: reject before any workspace mutation.
- Browser privacy boundary: local drafts must not imply CLI/cloud sync or transmit data.

## Planned File Map
- Modify `allinagent/memory.py` and `allinagent/project.py` for atomic writes and explicit error reporting.
- Create `allinagent/backup/{__init__.py,store.py}`; `allinagent/transfer/{__init__.py,package.py}`.
- Modify `allinagent/cli.py` for backup, restore, export, and import commands.
- Create `tests/test_memory_reliability.py`, `tests/test_backup.py`, `tests/test_transfer.py`, and `tests/test_web_shell.py`.
- Create `web/index.html`, `web/styles.css`, `web/app.js`, and `web/README.md`.
- Update `allinagent/__init__.py`, `pyproject.toml`, and `README.md` only after features pass tests.

---

## Task 1 — Reliable Memory Persistence

**Interfaces:** Preserve existing public `LocalMemory` and `ProjectMemory` methods and JSON formats. Add a small internal standard-library atomic JSON writer.

- [ ] Add tests for valid legacy records, 1,000-entry cap, and recent-entry limits.
- [ ] Run `python -m pytest tests/test_memory_reliability.py -q`; confirm new failure tests fail for the intended reasons.
- [ ] Add tests for malformed/truncated JSON and read/write/replace errors; assert the original file is preserved and errors are visible without printing stored text.
- [ ] Implement same-directory temporary write, flush/close, atomic replace, cleanup on failure, and load diagnostics.
- [ ] Apply safe persistence to project metadata without changing its schema.
- [ ] Run `python -m pytest tests/test_memory_reliability.py tests/test_safety.py -q`.
- [ ] Commit: `fix: make local memory persistence reliable`.

## Task 2 — Verified Backup and Restore

**Interfaces:**
- `create_backup(workspace: Path, backup_root: Path | None = None) -> Path`
- `list_backups(backup_root: Path | None = None) -> list[dict]`
- `verify_backup(backup_path: Path) -> dict`
- `restore_backup(workspace: Path, backup_path: Path, *, replace: bool = False) -> dict`

- [ ] Test backup manifests: format version, UTC timestamp, file/record counts, and SHA-256 digests.
- [ ] Implement backup/list using standard-library JSON; store backups outside application code and document the default location.
- [ ] Test malformed manifests, unsupported versions, invalid paths, changed digests, and oversized data.
- [ ] Implement strict verification and staged restore; checkpoint current data first and refuse to replace changed data unless explicitly confirmed.
- [ ] Add CLI commands for backup create/list/verify and restore; non-interactive replacement must require an explicit option.
- [ ] Run `python -m pytest tests/test_backup.py tests/test_cli_features.py tests/test_safety.py -q`.
- [ ] Commit: `feat: add verified local backups and restore`.

## Task 3 — Safe Export and Import

**Interfaces:**
- `export_workspace(workspace: Path, output_path: Path, *, include_memory: bool = True, include_project: bool = True) -> dict`
- `inspect_package(package_path: Path) -> dict`
- `import_workspace(workspace: Path, package_path: Path, *, conflict: str = "preserve") -> dict`

- [ ] Add failing round-trip tests for memory and project metadata; assert source files remain unchanged.
- [ ] Implement a versioned ZIP package with manifest, SHA-256 digests, supported JSON files only, and bounded archive/payload sizes.
- [ ] Test invalid ZIPs, path traversal, malformed schema, unsupported version, bad digests, and oversized entries; assert no live files change.
- [ ] Implement full validation before writes, deterministic duplicate handling, conflict reporting, and default preservation of existing data.
- [ ] Add `allinagent export <path>` and `allinagent import <path>`; require explicit confirmation for replace behavior.
- [ ] Simulate import write failure and verify current data can be recovered and success is not falsely reported.
- [ ] Run `python -m pytest tests/test_transfer.py tests/test_backup.py tests/test_safety.py -q`.
- [ ] Commit: `feat: add validated workspace export and import`.

## Task 4 — Browser Workspace Foundation

- [ ] Add static checks for accessible navigation, local-only notice, and no embedded credentials or unsupported sync claims.
- [ ] Create semantic `web/index.html` with product information and a simple draft workspace; style it responsively in `web/styles.css`.
- [ ] Implement create/view/delete draft conversations in `web/app.js` using namespaced browser localStorage only. Handle malformed data or disabled storage without crashing.
- [ ] Document how to open the site and its limits: no CLI file access, cloud AI, account sync, or cross-device storage.
- [ ] Run `python -m pytest tests/test_web_shell.py -q`; manually test keyboard use, narrow viewport, draft CRUD, and unavailable storage.
- [ ] Commit: `feat: add standalone browser workspace foundation`.

## Task 5 — Release Metadata and Full Verification

- [ ] Add a version consistency test for package metadata, CLI `--version`, and README.
- [ ] After Tasks 1–4 pass, set package version to `1.6.0` and update README with tested commands, data locations, privacy boundaries, and limitations.
- [ ] Run `python -m pytest tests/ -v`, `python -m compileall allinagent`, `python -m pip wheel . -w /tmp/allinagent-dist`, and `python -m allinagent --version`.
- [ ] Review `git diff --check` and the full diff for secrets, unrelated changes, destructive operations, and misleading cloud/model claims.
- [ ] Commit: `release: prepare ALLINAGENT v1.6.0`.

## Phase Gates
1. Memory and backup/restore tests pass before transfer work.
2. Export/import integrity and conflict tests pass before web work.
3. Web privacy boundary is tested and documented before version bump.
4. Do not describe account sync, cloud AI, or wired PC-to-PC transfer as implemented in v1.6.0 unless separately built and verified.

**Execution handoff:** This is a plan only. Do not modify product code until the user reviews the plan and selects an execution method.
