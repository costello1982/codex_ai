"""YAML helpers."""
from __future__ import annotations

import yaml


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False)
