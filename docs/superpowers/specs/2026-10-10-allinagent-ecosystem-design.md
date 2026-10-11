# ALLINAGENT Ecosystem v1.5 Design Specification

**Status:** Draft for user review  
**Date:** 2026-10-10  
**Repository:** `camdenl48799-create/ALLINAGENT`  
**Design scope:** One repository containing the existing Python CLI agent, memory and recovery improvements, data transfer tools, and a separately run browser workspace.

## 1. Purpose and goals

ALLINAGENT should remain a local-first PC coding agent while growing into a connected ecosystem. The work must preserve existing CLI behavior and user data, improve the reliability of saved memory, provide safe export/import and recovery, and add a browser-based workspace in the same Git repository without tangling its runtime with the Python CLI.

### Success criteria

- Existing CLI commands and safety controls continue to work.
- Memory save failures are visible rather than silently treated as success.
- Backups can be validated before restore; a restore does not silently overwrite newer data.
- Export/import validates data integrity and never deletes the source as part of a successful transfer.
- A website can be developed and tested independently from the Python package while living in this repository.
- Tests cover malformed data, failed writes, interrupted transfers, conflicts, and privacy boundaries.
- Documentation accurately describes what works locally versus what requires hosting, a companion process, or an online service.

## 2. Existing context and constraints

The repository currently describes ALLINAGENT v1.4.0 as a Python 3.10+ local-first CLI. The package entry point is `allinagent.cli:main`; the project uses setuptools and has an optional external LLM dependency. The README documents `allinagent/memory.py` as conversation memory and `allinagent/project.py` as project context storage.

The current `LocalMemory` implementation writes `.allinagent-memory.json` in the configured workspace. It stores timestamped prompt/response pairs, caps history at 1,000 entries, and currently suppresses save errors. Invalid or unreadable JSON currently loads as an empty list, which can make damaged memory appear absent. Project memory is stored at `.allinagent/project.json` and also suppresses some write errors.

Constraints:
- Preserve the current Python CLI and local-first behavior.
- External model use remains opt-in; this project does not claim a trained, first-party One- model exists today.
- No paid server or online sync service is assumed available.
- Do not expose secrets or one account's private conversations to another account.
- A browser page alone cannot access arbitrary local files, communicate with the CLI, or perform direct USB PC-to-PC transfer. Such features require explicit file selection, a supported companion process, or a future native component.
- Do not promise loss-proof storage; use validation, backups, and honest failure reporting to reduce risk.

## 3. Repository architecture

Keep one Git repository with independent modules and separate runtime/test boundaries:

- `allinagent/`: existing Python CLI and core agent.
- `allinagent/backup/` (or an equivalently small, clearly bounded module): backup creation, validation, listing, and restore operations.
- `allinagent/transfer/` (or an equivalently small module): portable export/import, integrity checks, conflict handling, and resumable transfer primitives.
- `web/`: separate browser workspace and public site, with its own dependency manifest and test/build commands.
- `tests/`: Python regression tests plus focused backup/transfer tests. Web tests should remain independently runnable from the web directory or a documented root command.
- `docs/superpowers/specs/`: reviewed design specifications.

Names and boundaries may be adjusted during implementation if inspection shows a better fit, but the CLI package and browser application must remain independently testable.

## 4. Memory reliability and recovery

### 4.1 Safe writes
- Save through a temporary file in the same directory, flush and close it, then replace the destination atomically where supported.
- Do not silently discard persistence errors. Surface a clear status or warning to the caller and keep the in-memory operation's outcome distinct from durable-save success.
- Keep a valid previous copy before replacing the primary memory file.
- Avoid logging message bodies, tokens, or secrets in error output.

### 4.2 Backup behavior
- Provide a user-invoked backup/list/verify/restore workflow first. Automatic backup cadence can be added only after its storage limits and retention behavior are defined.
- Store backups separately from application code and updates, in a documented user-data location.
- Include a format version, creation timestamp, record count, and integrity digest/manifest.
- Validate format, size, digest, and schema before a backup is considered restorable.
- Retain multiple backups under a documented retention policy; never remove the last known-good backup.
- Restore into a staged copy, validate it, and preserve the current primary data before switching to the restored version.
- If there is no valid recovery source, report that clearly instead of claiming the data was restored.

### 4.3 Recovery UX
- Add discoverable CLI commands for backup listing, verification, and recovery (exact command spelling to be finalized in the implementation plan).
- The recovery path should identify candidate backups and their dates, explain which data would be restored, and require confirmation before replacing current data.
- Prefer merging non-conflicting conversations when practical; where records conflict, preserve both or request a clear choice rather than silently choosing an older record.
- Do not make normal users perform manual JSON repair for common recoverable failures.

## 5. Data export and transfer

### 5.1 Initial supported workflow
- Implement portable export/import for conversation memory and project metadata first.
- Exports must be versioned and include a manifest with record counts and integrity checks.
- Import must validate the full payload before changing live data.
- Handle duplicates and conflicts deterministically; report skipped, imported, and conflicted records.
- Keep the source export and original local data untouched after import.
- For large transfers, use bounded chunks and support safe retry/resume where feasible.

### 5.2 Future PC-to-PC transfer
- Design transfer primitives so a later companion/native component can use them over a wired connection.
- Wired transfer is a future capability, not a browser-only promise. Any implementation must authenticate/confirm the receiving device, verify each chunk, support retries, and preserve source data until the destination is fully verified.
- Bluetooth is optional future scope and must not block a reliable file-based export/import implementation.

## 6. Browser workspace and public website

- Place the web app under `web/` and give it a separate build/test workflow.
- Initial delivery should focus on the public product site and a functional local browser workspace shell, with clearly labeled capabilities.
- Browser-local data must be clearly distinguished from data saved by the Python CLI or synchronized online.
- Do not imply browser chats are automatically available in the CLI or across PCs until a tested integration and storage service exist.
- Keep authentication, account sync, paid plans, and cloud model execution out of the first web milestone unless separately designed and approved.
- Never put private API keys, payment secrets, or privileged credentials in browser code.
- The future One- model family is a product direction; the initial workspace must not falsely claim that a proprietary foundation model is already available.

## 7. Privacy and account boundaries

- Local data remains local unless the user explicitly exports or enables a future sync feature.
- A shared PC does not mean all account conversations become visible to every account. Shared project data must be explicitly marked shared and separated from private conversation data.
- Export should allow users to inspect what is included before creating a package.
- Importing into a different account must be an explicit user action and must not automatically merge private data.
- Secrets and credentials should be excluded from export by default where identifiable, with clear warnings for user-created content that may contain secrets.

## 8. Error handling and safety

- Treat unreadable, malformed, incomplete, or digest-mismatched data as damaged; preserve it for diagnosis rather than silently replacing it.
- Avoid destructive restore/import behavior by staging, validating, checkpointing current data, and asking for confirmation when existing data would change.
- Never delete source data as part of transfer.
- Use bounded retries and meaningful failure messages; do not claim a save, backup, restore, import, sync, or transfer succeeded without verifying the result.
- Maintain existing write permissions, sandbox protections, shell permissions, and dry-run behavior.

## 9. Test strategy

Python tests should cover:
- normal memory save/load and backward compatibility with existing JSON;
- atomic-write failure and clear failure reporting;
- malformed and truncated memory files;
- backup creation, digest/schema verification, retention, and restore;
- refusal to overwrite newer data without a deliberate merge/replace choice;
- export/import round trips, duplicate records, conflicting records, corrupt packages, and interrupted/resumed transfers;
- privacy filtering and source preservation;
- existing CLI behavior and safety regression tests.

Web tests should cover:
- independent build and test commands;
- responsive and accessible basic navigation;
- clear separation between browser-local workspace state and CLI/cloud data;
- no embedded credentials or unsupported integration claims.

Run the existing test suite and relevant new tests before claiming a feature is complete. Document commands and actual outcomes.

## 10. Phased delivery

1. **Phase 1 — memory durability and recovery:** inspect all memory call sites and tests; improve safe persistence, add backup verification and recovery, and preserve backward compatibility.
2. **Phase 2 — data export/import:** add versioned packages, integrity checks, conflict reporting, and safe import/export.
3. **Phase 3 — web workspace foundation:** add the separately runnable `web/` app and public-site/workspace shell, without pretending it has cloud AI or automatic CLI access.
4. **Phase 4 — integration design:** only after the first three phases are validated, separately design account identity, optional sync, and companion-assisted PC-to-PC transfer.

Each phase should have its own implementation tasks and tests. The whole ecosystem is not considered complete merely because the website shell exists.

## 11. Out of scope for this specification

- Training or releasing a proprietary One- foundation model.
- Launching paid subscriptions, payment processing, or account recovery services.
- Automatic cloud sync or cross-device identity before a backend and threat model are approved.
- Guaranteed recovery when all copies of the user's data are lost or damaged.
- Direct USB or Bluetooth transfer implemented solely in browser JavaScript.
- Replacing the existing CLI with a web-only product.

## 12. Open implementation details

The implementation plan must resolve the exact CLI command names, user-data/backup directory conventions across Windows/macOS/Linux, backup retention defaults, archive format, checksum algorithm, and web framework. These choices must preserve existing data and avoid adding unnecessary dependencies.
