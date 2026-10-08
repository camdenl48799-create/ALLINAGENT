"""Model capability routing for ALLINAGENT v1.5.0.

Models are configured by the user; ALLINAGENT never requires a paid provider.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelProfile:
    name: str
    specialties: tuple[str, ...]

PROFILES=(
    ModelProfile("allinone-coding", ("coding", "debugging", "refactoring")),
    ModelProfile("allinone-game", ("game-dev", "c++", "c#", "lua", "luau", "shaders", "engines")),
    ModelProfile("allinone-reasoning", ("planning", "architecture", "requirements")),
    ModelProfile("allinone-general", ("general", "research", "creation")),
)

def choose_profile(prompt: str) -> ModelProfile:
    text=prompt.casefold()
    if any(x in text for x in ("unreal", "unity", "godot", "roblox", "lua", "luau", "c++", "shader", "game")): return PROFILES[1]
    if any(x in text for x in ("debug", "fix", "refactor", "code", "python", "javascript", "typescript")): return PROFILES[0]
    if any(x in text for x in ("plan", "architecture", "requirements", "design")): return PROFILES[2]
    return PROFILES[3]

def model_status() -> str:
    return "ALLINAGENT MODEL LAYER\n\n" + "\n".join(f"- {p.name}: {', '.join(p.specialties)}" for p in PROFILES) + "\n\nExternal providers remain optional."
