"""Render baseline VXLAN EVPN configurations with Jinja2.

This script is intentionally verbose and heavily commented so that engineers who
are new to Python can follow the flow and reuse the structure in their own
projects. The goal is to take structured data (a JSON inventory) and feed it
into a Jinja template so we receive consistent, production-ready configs for
all node roles (leaf, spine, border leaf, and border gateway).

The script only renders configuration files to disk; it never touches a
physical device. Use ``deploy_fabric_configs.py`` if you want to connect to the
switches and push the configuration.
"""
from __future__ import annotations

import json
from ipaddress import ip_network
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def load_fabric_variables(variables_file: Path) -> Dict:
    """Return the structured data we maintain in ``fabric_variables.json``.

    Keeping the details in JSON decouples data from code so we can version the
    business intent (loopback prefix, role assignments, multicast group, and so
    on) independently from the Python logic. Any automation platform—Python or
    otherwise—can parse JSON, which makes this format future proof.
    """

    with variables_file.open(encoding="utf-8") as handle:
        return json.load(handle)


def calculate_loopback_ip(prefix: str, loopback_id: int) -> str:
    """Derive a /32 loopback address from the shared prefix and host ID.

    The JSON file contains a ``loopback_id`` for every node. We add that value
    to the network address of the prefix to deterministically produce the
    per-device loopback. This keeps things simple: leaf01 uses ID 1, leaf02 uses
    ID 2, border leafs start at 201, and border gateways start at 301. If you
    prefer a different scheme, just adjust the numbers in the JSON file.
    """

    network = ip_network(prefix)
    host = network.network_address + loopback_id
    return str(host)


def enrich_devices(fabric: Dict) -> List[Dict]:
    """Attach computed values and validation data to every device entry."""

    devices = fabric["devices"]
    loopback_prefix = fabric["loopback_prefix"]

    # Build an index by hostname so we can look up peers quickly later on.
    index = {device["name"]: device for device in devices}

    # Track vPC domain IDs to guard against duplicates.
    vpc_domain_tracker = {}

    for device in devices:
        device["loopback_ip"] = calculate_loopback_ip(loopback_prefix, device["loopback_id"])

        # Attach downlink metadata that the Jinja template expects for spines.
        if device["role"] == "spine":
            device["downlinks"] = [
                {
                    "name": peer["name"],
                    "ip": calculate_loopback_ip(loopback_prefix, peer["loopback_id"]),
                }
                for peer in devices
                if peer["role"] != "spine"
            ]

        # When a device participates in a vPC we use the index to fetch details
        # about the peer. These additional fields help the template render
        # peer-keepalive and deterministic role priorities.
        if device.get("vpc"):
            peer_name = device["vpc"]["peer"]
            peer = index.get(peer_name)
            if not peer:
                raise ValueError(f"vPC peer {peer_name} for {device['name']} not found")

            # ``setdefault`` initializes the set only once. We then raise an
            # exception if two different pairs try to reuse the same domain ID.
            domain_id = device["vpc"]["domain_id"]
            owners = vpc_domain_tracker.setdefault(domain_id, set())
            owners.add(device["name"])
            if len(owners) > 2:
                raise ValueError(
                    f"vPC domain {domain_id} used by more than two switches: {owners}"
                )

            device["vpc_peer_mgmt_ip"] = peer["mgmt_ip"]
            # Lower priority wins the primary role; odd/even split keeps it easy.
            device["vpc_role_priority"] = 10 if device["name"].endswith("1") else 20

    return devices


def render_configs() -> None:
    """Generate per-device configuration files under ``rendered-configs``."""

    variables_path = Path(__file__).with_name("fabric_variables.json")
    fabric = load_fabric_variables(variables_path)
    devices = enrich_devices(fabric)

    output_dir = Path(__file__).with_name("rendered-configs")
    output_dir.mkdir(exist_ok=True)

    # Jinja needs to know where the template files live. ``FileSystemLoader``
    # points to the ``templates`` directory alongside this script.
    environment = Environment(loader=FileSystemLoader(Path(__file__).with_name("templates")))
    template = environment.get_template("device_full_config.j2")

    for device in devices:
        rendered = template.render(
            fabric_name=fabric["fabric_name"],
            multicast_group=fabric["multicast_group"],
            bgp_asn=fabric["bgp_asn"],
            evpn_rrs=fabric["evpn_rrs"],
            device=device,
        )

        filename = output_dir / f"{device['name']}.cfg"
        with filename.open("w", encoding="utf-8") as handle:
            handle.write(rendered)

        print(f"Rendered configuration for {device['name']} -> {filename}")


if __name__ == "__main__":
    render_configs()
