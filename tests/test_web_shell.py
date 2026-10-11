from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_workspace_has_accessible_navigation_and_local_privacy_notice():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<html lang="en">' in html
    assert '<nav aria-label="Main navigation">' in html
    assert 'aria-live="polite"' in html
    assert "not uploaded" in html
    assert 'id="draft-form"' in html


def test_workspace_uses_browser_local_storage_without_sync_claims():
    js = (WEB / "app.js").read_text(encoding="utf-8")
    readme = (WEB / "README.md").read_text(encoding="utf-8")
    assert "localStorage.setItem" in js
    assert "localStorage.getItem" in js
    assert "No network sync" in js
    assert "do not sync across devices" in readme
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js


def test_workspace_has_no_embedded_credentials_or_external_scripts():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "api_key" not in html.lower()
    assert "api_key" not in js.lower()
    assert "https://" not in html
    assert 'src="app.js"' in html
    assert 'href="styles.css"' in html
