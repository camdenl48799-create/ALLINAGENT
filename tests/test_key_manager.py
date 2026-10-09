import pytest

from allinagent.key_manager import APIKeyManager, KeyManagerError, scope_allows


def test_model_key_is_generated_once_and_scoped(tmp_path):
    manager = APIKeyManager(tmp_path / "keys.sqlite3")
    created = manager.create_key("Search app", kind="model", models=["you.com", "gpt"])
    assert created["api_key"].startswith("aia_live_")
    assert set(created["scopes"]) == {"you.com", "gpt"}
    verified = manager.verify_key(created["api_key"])
    assert verified["id"] == created["id"]
    assert scope_allows(verified, "you.com")
    assert not scope_allows(verified, "another-provider")
    assert "api_key" not in manager.list_keys()[0]
    assert created["api_key"] not in str(manager.list_keys())


def test_everything_key_has_all_scopes(tmp_path):
    manager = APIKeyManager(tmp_path / "keys.sqlite3")
    created = manager.create_key("My ALLINAGENT app", kind="everything")
    verified = manager.verify_key(created["api_key"])
    assert verified["scopes"] == ["*"]
    assert scope_allows(verified, "any-provider")


def test_revoked_key_no_longer_verifies(tmp_path):
    manager = APIKeyManager(tmp_path / "keys.sqlite3")
    created = manager.create_key("Temporary", kind="everything")
    assert manager.revoke_key(created["id"])
    assert manager.verify_key(created["api_key"]) is None
    assert not manager.revoke_key(created["id"])


def test_model_key_requires_scope(tmp_path):
    manager = APIKeyManager(tmp_path / "keys.sqlite3")
    with pytest.raises(KeyManagerError):
        manager.create_key("Missing scope", kind="model")


def test_invalid_kind_rejected(tmp_path):
    manager = APIKeyManager(tmp_path / "keys.sqlite3")
    with pytest.raises(KeyManagerError):
        manager.create_key("Bad", kind="provider-master")


def test_unknown_and_malformed_keys_fail(tmp_path):
    manager = APIKeyManager(tmp_path / "keys.sqlite3")
    assert manager.verify_key("not-a-key") is None
    assert manager.verify_key("aia_live_not-real") is None
