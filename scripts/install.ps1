# ALLINAGENT bootstrap installer for Windows PowerShell.
# Downloads the source archive, creates an isolated virtual environment,
# installs ALLINAGENT locally, and verifies the CLI.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1

[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "ALLINAGENT"),
    [string]$Repo = "camdenl48799-create/ALLINAGENT",
    [string]$Ref = "main"
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) { Write-Host "[ALLINAGENT] $Message" }
function Fail([string]$Message) { Write-Error "[ALLINAGENT] $Message"; exit 1 }

try {
    Write-Step "Checking Python 3.10+..."
    $python = Get-Command py -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
    if (-not $python) { Fail "Python 3.10+ is required. Install Python, then run this installer again." }

    $versionText = & $python.Source -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
    $version = [version]$versionText.Trim()
    if ($version.Major -lt 3 -or ($version.Major -eq 3 -and $version.Minor -lt 10)) { Fail "Python 3.10+ is required. Found $versionText." }

    $tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("allinagent-" + [guid]::NewGuid().ToString("N"))
    $archive = Join-Path $tempRoot "source.zip"
    $extract = Join-Path $tempRoot "source"
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    try {
        Write-Step "Downloading ALLINAGENT source from GitHub..."
        $url = "https://github.com/$Repo/archive/refs/heads/$Ref.zip"
        Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing
        Write-Step "Extracting..."
        Expand-Archive -Path $archive -DestinationPath $extract -Force
        $source = Get-ChildItem -Path $extract -Directory | Select-Object -First 1
        if (-not $source) { Fail "The downloaded archive did not contain a source directory." }

        Write-Step "Creating isolated environment at $InstallRoot..."
        New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
        $venv = Join-Path $InstallRoot ".venv"
        & $python.Source -m venv $venv
        if ($LASTEXITCODE -ne 0) { Fail "Python could not create the virtual environment." }
        $venvPython = Join-Path $venv "Scripts\python.exe"
        if (-not (Test-Path $venvPython)) { Fail "The virtual environment was not created correctly." }

        Write-Step "Installing ALLINAGENT locally..."
        & $venvPython -m pip install $source.FullName
        if ($LASTEXITCODE -ne 0) { Fail "ALLINAGENT installation failed." }
        Write-Step "Verifying installation..."
        & $venvPython -m allinagent --help | Out-Null
        if ($LASTEXITCODE -ne 0) { Fail "ALLINAGENT installed but verification failed." }

        $launcherDir = Join-Path $InstallRoot "bin"
        New-Item -ItemType Directory -Force -Path $launcherDir | Out-Null
        $launcher = Join-Path $launcherDir "allinagent.cmd"
        $launcherText = "@echo off`r`n`"$venvPython`" -m allinagent %*`r`n"
        Set-Content -Path $launcher -Value $launcherText -Encoding ASCII

        Write-Step "Installed successfully."
        Write-Host ""
        Write-Host "ALLINAGENT is ready at: $InstallRoot"
        Write-Host "For this PowerShell session: & `"$launcher`" activate"
        Write-Host "Add $launcherDir to PATH to use: allinagent activate"
    } finally {
        if (Test-Path $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue }
    }
} catch { Fail $_.Exception.Message }
