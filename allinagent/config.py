from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    model: str
    max_steps: int = 12


def load_config(
    *,
    model: str | None = None,
    base_url: str | None = None,
    max_steps: int | None = None,
) -> Config:
    api_key = (
        os.environ.get("ALLINAGENT_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )
    resolved_base = (
        base_url
        or os.environ.get("ALLINAGENT_BASE_URL")
        or "https://api.openai.com/v1"
    )
    resolved_model = (
        model
        or os.environ.get("ALLINAGENT_MODEL")
        or "gpt-4o-mini"
    )
    steps = max_steps if max_steps is not None else 12
    return Config(
        api_key=api_key,
        base_url=resolved_base.rstrip("/"),
        model=resolved_model,
        max_steps=max(1, steps),
    )
