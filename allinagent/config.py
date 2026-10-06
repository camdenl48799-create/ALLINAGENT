"""Configuration for ALLINAGENT. Local mode needs no API key."""
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None

    @classmethod
    def from_env(cls, *, api_key=None, base_url=None, model=None):
        return cls(api_key or os.getenv("ALLINAGENT_API_KEY") or os.getenv("OPENAI_API_KEY"), base_url or os.getenv("ALLINAGENT_BASE_URL"), model or os.getenv("ALLINAGENT_MODEL"))

    @property
    def has_llm(self) -> bool:
        return bool(self.api_key)
