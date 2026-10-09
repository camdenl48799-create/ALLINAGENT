# ALLINAGENT API Key Manager

The local API Key Manager can issue two types of **ALLINAGENT-owned application keys**:

- **Normal model key** — restricted to the model/provider scopes you specify.
- **Everything key** — a master scope (`*`) intended for a trusted app that needs all integrations supported by your own ALLINAGENT host.

## Important distinction

These are credentials issued by your local ALLINAGENT installation. They do **not** create or replace You.com, OpenAI, or other provider-issued API keys, and they do not provide free access to paid models. Provider credentials must still be configured separately. An `everything` key only grants the scopes that the host application actually implements and enforces.

## Python usage

```python
from allinagent.key_manager import APIKeyManager, scope_allows

manager = APIKeyManager()  # stores metadata under .allinagent/api_keys.sqlite3

# A key restricted to specific provider/model scopes
normal = manager.create_key(
    "My search app",
    kind="model",
    models=["you.com", "my-model-provider"],
)
print(normal["api_key"])  # display/copy once; do not log or commit it

# A master-scope key for a trusted ALLINAGENT-connected app
master = manager.create_key("My ALLINAGENT app", kind="everything")
print(master["api_key"])  # display/copy once; keep private

# On each incoming request, verify the token and enforce its scope:
key_info = manager.verify_key(presented_token)
if key_info is None:
    raise PermissionError("Invalid or revoked ALLINAGENT key")
if not scope_allows(key_info, requested_provider):
    raise PermissionError("This key does not allow that provider")
```

## Management

```python
manager.list_keys()             # safe metadata only; never returns secrets
manager.revoke_key("key_id")    # immediately disables the key
```

The full token is returned only when created. The SQLite database stores a SHA-256 hash, not the plaintext key, and attempts to restrict file permissions where supported. Keep the database private and back it up securely. If a key is exposed, revoke it and create a replacement.

## Production notes

- Call `verify_key()` on every protected request and enforce the returned scopes server-side.
- Do not ship an `everything` key inside a desktop app, browser bundle, public repository, or mobile app. Anyone who extracts it could use its full scope.
- Use per-user/per-app keys with the narrowest scope practical.
- Add rate limits, usage quotas, audit logs, and a secure HTTPS API gateway before exposing this manager to multiple users or the public internet.
- This module is a local key-management building block; it does not itself run an HTTP API server or proxy provider calls.
