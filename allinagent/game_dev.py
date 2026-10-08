"""Game-development capability metadata for ALLINAGENT v1.5.0."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

LANGUAGES = {
    "C": [".c", ".h"], "C++": [".cpp", ".cc", ".cxx", ".hpp"],
    "C#": [".cs"], "Lua": [".lua"], "Luau": [".luau"],
    "Python": [".py"], "JavaScript": [".js", ".mjs"], "TypeScript": [".ts", ".tsx"],
    "GLSL": [".glsl", ".vert", ".frag"], "HLSL": [".hlsl"],
}
ENGINES = {
    "Unreal Engine": [".uproject"], "Unity": ["Assets", "ProjectSettings", "Packages"],
    "Godot": ["project.godot"], "Roblox Studio": [".rbxl", ".rbxlx"],
}

@dataclass(frozen=True)
class GameProjectReport:
    engines: list[str]
    languages: list[str]
    capabilities: tuple[str, ...]

    def summary(self) -> str:
        return ("ALLINAGENT GAME DEV MODE\n\n"
                f"Engines: {', '.join(self.engines) or 'not detected'}\n"
                f"Languages: {', '.join(self.languages) or 'not detected'}\n\n"
                "Core capabilities: " + ", ".join(self.capabilities))

def inspect_game_project(workspace: Path) -> GameProjectReport:
    engines=[]; languages=set()
    for name, markers in ENGINES.items():
        if any((workspace / m).exists() for m in markers) or (name == "Unity" and (workspace/"Assets").exists()): engines.append(name)
    for p in workspace.rglob("*"):
        if not p.is_file(): continue
        for lang, exts in LANGUAGES.items():
            if p.suffix.casefold() in {x.casefold() for x in exts}: languages.add(lang)
    capabilities=("exact prompt implementation", "multi-file game architecture", "debug/build/test/fix", "performance-aware code", "shader support", "engine-aware project edits")
    return GameProjectReport(engines, sorted(languages), capabilities)
