from pathlib import Path
import subprocess
import sys

from allinagent import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_package_cli_and_readme_versions_match():
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    metadata_version = next(line.split("=", 1)[1].strip().strip('"') for line in project.splitlines() if line.startswith("version = "))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "allinagent", "--version"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert __version__ == "1.6.0"
    assert metadata_version == __version__
    assert f"v{__version__} — Current release" in readme
    assert result.stdout.strip() == f"allinagent {__version__}"
