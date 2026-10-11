# You.com Web Search in ALLINAGENT

ALLINAGENT can use You.com web search from the optional LLM tool loop.

## Configure the key

The official You.com environment variable is `YDC_API_KEY`. For compatibility,
ALLINAGENT also accepts `YOU_API_KEY`.

**Never paste an API key into source code, README files, issues, pull requests, or logs.**
If a key has been shared publicly or in a chat, revoke/rotate it and use the replacement.

### Windows PowerShell (current terminal only)

This prompts without echoing the key, then sets it for the current PowerShell session:

```powershell
$secure = Read-Host "Enter You.com API key" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $env:YDC_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
```

Then run ALLINAGENT with optional model support enabled (You.com search is a tool
available to the model during that run). Your configured LLM provider is still
needed for model reasoning; the You.com key supplies web-search results, not a
general-purpose chat model.

## What it does

- Sends a POST request to `https://ydc-index.io/v1/search` with the `X-API-Key` header.
- Returns a limited number of web/news results with source URLs and summaries.
- Handles missing credentials, invalid scopes, rate limits, and connection errors without printing the secret.
- Uses Python's standard library; no extra package is required for web search.

Search requests may incur API usage or costs according to your You.com account plan.
