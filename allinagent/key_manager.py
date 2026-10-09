"""Local API key manager for ALLINAGENT-owned applications.

Generated keys authenticate to an application that integrates this manager; they
are NOT provider-issued keys and cannot replace keys from model/API providers.
Only SHA-256 hashes of high-entropy generated tokens are stored on disk. The
plaintext token is returned only by create_key() and should be shown once.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class KeyManagerError(ValueError):
    """Raised when a key request is invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class APIKeyManager:
    """Create and manage locally issued ALLINAGENT keys using SQLite.

    ``kind="model"`` creates a key limited to the named model/provider scopes.
    ``kind="everything"`` creates a master-scope key for every integration
    enforced by the host application. The manager does not itself proxy requests
    or grant access to third-party services; callers must check ``verify_key``
    and enforce returned scopes on every protected operation.
    """

    def __init__(self, database: str | Path = ".allinagent/api_keys.sqlite3") -> None:
        self.database = Path(database).expanduser().resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('model', 'everything')),
                    prefix TEXT NOT NULL,
                    secret_hash TEXT NOT NULL UNIQUE,
                    scopes_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked_at TEXT
                )"""
            )
        # Best effort: restrict database permissions on platforms that support it.
        try:
            self.database.chmod(0o600)
        except OSError:
            pass

    def create_key(
        self,
        name: str,
        *,
        kind: str = "model",
        models: Iterable[str] = (),
    ) -> dict[str, Any]:
        """Create a key and return its plaintext once alongside safe metadata."""
        clean_name = name.strip() if isinstance(name, str) else ""
        if not clean_name or len(clean_name) > 100:
            raise KeyManagerError("Key name must be between 1 and 100 characters.")
        if kind not in {"model", "everything"}:
            raise KeyManagerError("Key kind must be 'model' or 'everything'.")

        if kind == "everything":
            scopes = ["*"]
        else:
            scopes = sorted({m.strip() for m in models if isinstance(m, str) and m.strip()})
            if not scopes:
                raise KeyManagerError("A normal model key must include at least one model/provider scope.")
            if any(len(scope) > 120 for scope in scopes):
                raise KeyManagerError("Model/provider scopes must be 120 characters or fewer.")

        token = "aia_live_" + secrets.token_urlsafe(32)
        key_id = "key_" + secrets.token_hex(8)
        prefix = token[:18]
        created_at = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO api_keys (id,name,kind,prefix,secret_hash,scopes_json,created_at) VALUES (?,?,?,?,?,?,?)",
                (key_id, clean_name, kind, prefix, _digest(token), json.dumps(scopes), created_at),
            )
        return {
            "id": key_id,
            "name": clean_name,
            "kind": kind,
            "prefix": prefix,
            "scopes": scopes,
            "created_at": created_at,
            "api_key": token,
            "warning": "Copy this key now. The plaintext is not stored and cannot be shown again.",
        }

    def list_keys(self) -> list[dict[str, Any]]:
        """List key metadata without ever returning plaintext secrets or hashes."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,name,kind,prefix,scopes_json,created_at,revoked_at FROM api_keys ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "kind": row["kind"],
                "prefix": row["prefix"],
                "scopes": json.loads(row["scopes_json"]),
                "created_at": row["created_at"],
                "revoked_at": row["revoked_at"],
                "active": row["revoked_at"] is None,
            }
            for row in rows
        ]

    def revoke_key(self, key_id: str) -> bool:
        """Revoke a key by its public ID. Return False if it does not exist."""
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE api_keys SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
                (_utc_now(), key_id),
            )
            return cursor.rowcount == 1

    def verify_key(self, token: str) -> dict[str, Any] | None:
        """Verify a presented token and return its enforced scopes, or None.

        Call this on every protected request. A revoked or malformed key never
        verifies. The caller remains responsible for checking whether the key's
        scopes permit the requested provider/model/action.
        """
        if not isinstance(token, str) or not token.startswith("aia_live_"):
            return None
        token_hash = _digest(token)
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,name,kind,prefix,scopes_json,created_at,revoked_at,secret_hash FROM api_keys WHERE prefix=?",
                (token[:18],),
            ).fetchall()
        for row in rows:
            if row["revoked_at"] is not None:
                continue
            if hmac.compare_digest(token_hash, row["secret_hash"]):
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "kind": row["kind"],
                    "scopes": json.loads(row["scopes_json"]),
                    "created_at": row["created_at"],
                }
        return None


def scope_allows(key_info: dict[str, Any], requested_scope: str) -> bool:
    """Return whether verified key metadata grants a particular scope."""
    scopes = key_info.get("scopes", [])
    return "*" in scopes or requested_scope in scopes
