#!/usr/bin/env python3
"""OpenWebUI/OpenAI-compatible helper for NX-OS EVPN fabric generation and checks."""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
FABRIC_FILE = ROOT / "data" / "fabric.json"

SYSTEM_PROMPT = """
You are a Cisco NX-OS EVPN automation copilot.
- Use unnumbered interfaces for underlay.
- Underlay protocol is OSPF.
- Overlay protocol is BGP EVPN.
- Include Spine/Leaf/Border-Leaf, vPC pairs, and DCI border gateways.
- Prefer dynamic/subnet-based BGP neighbors with listen ranges where possible.
""".strip()


def call_openwebui(user_prompt: str, model: str = "gpt-4o-mini") -> str:
    base_url = os.getenv("OPENWEBUI_BASE_URL", "http://localhost:3000")
    api_key = os.getenv("OPENWEBUI_API_KEY", "")
    endpoint = f"{base_url.rstrip('/')}/api/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }

    response = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def main() -> None:
    fabric = FABRIC_FILE.read_text(encoding="utf-8")
    user_prompt = (
        "Generate deployment notes and a change-checklist for this Cisco NX-OS fabric JSON:\n"
        f"{fabric}"
    )
    print(call_openwebui(user_prompt=user_prompt))


if __name__ == "__main__":
    main()
