#!/usr/bin/env python3
"""Generate Cisco NX-OS VXLAN EVPN configs from JSON + Jinja2."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "fabric.json"
TEMPLATE_DIR = ROOT / "templates"
TEMPLATE_FILE = "nxos_vxlan_evpn.j2"
OUTPUT_DIR = ROOT / "generated"


def load_fabric_data(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def render_configs(payload: dict) -> dict[str, str]:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    template = env.get_template(TEMPLATE_FILE)

    rendered: dict[str, str] = {}
    for device in payload["devices"]:
        config = template.render(device=device, fabric=payload["fabric"])
        rendered[device["name"]] = config.rstrip() + "\n"
    return rendered


def write_configs(configs: dict[str, str], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for device, config in configs.items():
        outfile = output_dir / f"{device}.cfg"
        outfile.write_text(config, encoding="utf-8")


def main() -> None:
    payload = load_fabric_data(DATA_FILE)
    configs = render_configs(payload)
    write_configs(configs, OUTPUT_DIR)
    print(f"Rendered {len(configs)} configurations into {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
