"""Tests for Windows executable build orchestration."""
from pathlib import Path

import pytest

from allinagent.build import WindowsBuilder


def test_detect_python(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    result = WindowsBuilder(tmp_path).detect()
    assert result["type"] == "python"
    assert result["entry"] == "main.py"


def test_detect_dotnet(tmp_path: Path):
    (tmp_path / "Demo.csproj").write_text("<Project />\n", encoding="utf-8")
    result = WindowsBuilder(tmp_path).detect()
    assert result["type"] == "dotnet"
    assert result["entry"] == "Demo.csproj"


def test_unknown_project(tmp_path: Path):
    assert WindowsBuilder(tmp_path).detect()["type"] == "unknown"


def test_build_requires_shell_permission(tmp_path: Path):
    assert "BUILD DENIED" in WindowsBuilder(tmp_path).build()


def test_build_dry_run_does_not_execute(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    result = WindowsBuilder(tmp_path, allow_shell=True, dry_run=True).build()
    assert "BUILD BLOCKED" in result


@pytest.mark.parametrize("kind", ["dotnet", "python"])
def test_build_quotes_paths(tmp_path: Path, monkeypatch, kind: str):
    name = "O'Brien'; Write-Output $env:TEMP; 'back`tick"
    quoted_name = "O''Brien''; Write-Output $env:TEMP; ''back`tick"
    suffix = ".csproj" if kind == "dotnet" else ".py"
    source = tmp_path / (name + suffix)
    source.write_text("", encoding="utf-8")
    if kind == "python":
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    output = name + " output"
    exe = tmp_path / output / (name + ".exe")
    commands = []

    def run(command, timeout):
        commands.append(command)
        if len(commands) == 1:
            exe.parent.mkdir()
            exe.write_bytes(b"MZ")
        return 0, "ok"

    builder = WindowsBuilder(tmp_path, allow_shell=True)
    monkeypatch.setattr(builder, "_run_powershell", run)
    kwargs = {"project": source.name} if kind == "dotnet" else {"entry": source.name}
    result = builder.build(output=output, **kwargs)

    assert "BUILD COMPLETE" in result
    if kind == "dotnet":
        assert commands[0] == (
            f"dotnet publish '{quoted_name}.csproj' -c Release -r win-x64 "
            f"--self-contained true -p:PublishSingleFile=true -o '{quoted_name} output'"
        )
    else:
        assert commands[0] == (
            "python -m PyInstaller --noconfirm --clean --onefile --windowed "
            f"'{quoted_name}.py'"
        )
    assert commands[1] == (
        f"(Get-Item -LiteralPath '{quoted_name} output/{quoted_name}.exe').Length"
    )


@pytest.mark.parametrize("output", [None, "dist"])
@pytest.mark.parametrize("create_unrelated_exe", [False, True])
def test_build_exe_discovery_scope(tmp_path: Path, monkeypatch, output, create_unrelated_exe):
    (tmp_path / "Demo.csproj").write_text("<Project />", encoding="utf-8")
    (tmp_path / "old.exe").write_bytes(b"old executable")
    commands = []

    def run(command, timeout):
        commands.append(command)
        if create_unrelated_exe:
            (tmp_path / "new.exe").write_bytes(b"new executable")
        return 0, "ok"

    builder = WindowsBuilder(tmp_path, allow_shell=True)
    monkeypatch.setattr(builder, "_run_powershell", run)
    result = builder.build(output=output)

    if output is None and create_unrelated_exe:
        assert "BUILD COMPLETE" in result
        assert "new.exe" in result
        assert len(commands) == 2
    else:
        assert "BUILD FAILED" in result
        assert len(commands) == 1
        if output:
            assert "No .exe file was found in the output directory:" in result
        else:
            assert "No new .exe file was produced" in result


@pytest.mark.parametrize("preexisting", [False, True])
def test_build_finds_exe_in_explicit_output(tmp_path: Path, monkeypatch, preexisting: bool):
    (tmp_path / "Demo.csproj").write_text("<Project />", encoding="utf-8")
    exe = tmp_path / "dist" / "nested" / "app.exe"
    exe.parent.mkdir(parents=True)
    if preexisting:
        exe.write_bytes(b"old executable")
    # A directory with an EXE suffix must never be selected.
    (exe.parent / "directory.exe").mkdir()
    commands = []

    def run(command, timeout):
        commands.append(command)
        if len(commands) == 1:
            exe.write_bytes(b"rebuilt executable")
            (tmp_path / "unrelated.exe").write_bytes(b"unrelated executable")
        return 0, "ok"

    builder = WindowsBuilder(tmp_path, allow_shell=True)
    monkeypatch.setattr(builder, "_run_powershell", run)
    result = builder.build(output="dist")

    assert "BUILD COMPLETE" in result
    assert str(exe) in result
    assert commands[1] == "(Get-Item -LiteralPath 'dist/nested/app.exe').Length"
