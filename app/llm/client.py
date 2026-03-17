"""Minimal LLM client abstraction."""
from __future__ import annotations

from typing import Any


class LLMClient:
    """Simple pluggable interface; default implementation is deterministic stub."""

    def complete_json(self, prompt: str) -> dict[str, Any]:
        return {"raw": prompt}
