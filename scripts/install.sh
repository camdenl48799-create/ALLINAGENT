#!/usr/bin/env bash
# ALLINAGENT bootstrap installer for macOS and Linux.
# Downloads the source archive, creates an isolated virtual environment,
# installs ALLINAGENT locally, and verifies the CLI.
#
# Usage:
#   bash scripts/install.sh
#
# Override defaults with environment variables:
#   ALLINAGENT_INSTALL_ROOT="$HOME/.local/share/ALLINAGENT"
#   ALLINAGENT_REPO="camdenl48799-create/ALLINAGENT"
#   ALLINAGENT_REF="main"

set -euo pipefail

INSTALL_ROOT="${ALLINAGENT_INSTALL_ROOT:-$HOME/.local/share/ALLINAGENT}"
REPO="${ALLINAGENT_REPO:-camdenl48799-create/ALLINAGENT}"
REF="${ALLINAGENT_REF:-main}"

write_step() {
    echo "[ALLINAGENT] $1"
}

fail() {
    echo "[ALLINAGENT] ERROR: $1" >&2
    exit 1
}

# --- Check Python 3.10+ -----------------------------------------------------

write_step "Checking Python 3.10+..."

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        ver="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")"
        major="${ver%%.*}"
        minor="${ver#*.}"
        if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; }; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    fail "Python 3.10+ is required. Install Python, then run this installer again."
fi

write_step "Found: $($PYTHON --version)"

# --- Download and extract ---------------------------------------------------

TEMP_ROOT="$(mktemp -d /tmp/allinagent-XXXXXX)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

ARCHIVE="$TEMP_ROOT/source.zip"
EXTRACT="$TEMP_ROOT/source"

write_step "Downloading ALLINAGENT source from GitHub..."
URL="https://github.com/$REPO/archive/refs/heads/$REF.zip"

if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$ARCHIVE" "$URL"
elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$ARCHIVE" "$URL"
else
    fail "Neither curl nor wget is available. Please install one and retry."
fi

write_step "Extracting..."
mkdir -p "$EXTRACT"

if command -v unzip >/dev/null 2>&1; then
    unzip -q "$ARCHIVE" -d "$EXTRACT"
else
    # Fallback: Python can extract zip files
    "$PYTHON" -c "import zipfile, sys; zipfile.ZipFile('$ARCHIVE').extractall('$EXTRACT')"
fi

SOURCE="$(find "$EXTRACT" -maxdepth 1 -type d | tail -1)"
if [ ! -d "$SOURCE" ]; then
    fail "The downloaded archive did not contain a source directory."
fi

# --- Create virtual environment ---------------------------------------------

write_step "Creating isolated environment at $INSTALL_ROOT..."
mkdir -p "$INSTALL_ROOT"
VENV="$INSTALL_ROOT/.venv"

if ! "$PYTHON" -m venv "$VENV"; then
    fail "Python could not create the virtual environment."
fi

VENV_PYTHON="$VENV/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    fail "The virtual environment was not created correctly."
fi

# --- Install ----------------------------------------------------------------

write_step "Installing ALLINAGENT locally..."
if ! "$VENV_PYTHON" -m pip install "$SOURCE"; then
    fail "ALLINAGENT installation failed."
fi

write_step "Verifying installation..."
if ! "$VENV_PYTHON" -m allinagent --version >/dev/null 2>&1; then
    fail "ALLINAGENT installed but verification failed."
fi

# --- Create launcher --------------------------------------------------------

LAUNCHER_DIR="$INSTALL_ROOT/bin"
mkdir -p "$LAUNCHER_DIR"
LAUNCHER="$LAUNCHER_DIR/allinagent"

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV_PYTHON" -m allinagent "\$@"
EOF
chmod +x "$LAUNCHER"

# --- Done -------------------------------------------------------------------

write_step "Installed successfully."
echo ""
echo "ALLINAGENT is ready at: $INSTALL_ROOT"
echo "Launcher: $LAUNCHER"
echo ""
echo "Add to PATH for this session:"
echo "  export PATH=\"$LAUNCHER_DIR:\$PATH\""
echo ""
echo "Or add to your shell profile (~/.bashrc, ~/.zshrc):"
echo "  export PATH=\"$LAUNCHER_DIR:\$PATH\""
echo ""
echo "Then run: allinagent"
echo "Or run directly: $LAUNCHER"
