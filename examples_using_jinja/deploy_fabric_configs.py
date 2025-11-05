"""Connect to Nexus switches and push Jinja-rendered configurations.

The structure mirrors ``render_fabric_configs.py`` but adds the device
connection workflow. The script renders the configuration in-memory and then
uses Netmiko to stage the config as a candidate, show a diff, and optionally
commit it. Keeping rendering and deployment in separate functions makes it easy
for you to plug these helpers into larger frameworks such as Nornir.
"""
from __future__ import annotations

import json
from getpass import getpass
from ipaddress import ip_network
from pathlib import Path
from typing import Dict, Iterable

from jinja2 import Environment, FileSystemLoader
from netmiko import ConnectHandler


# -----------------------------------------------------------------------------
# Data loading helpers (identical to the render script)
# -----------------------------------------------------------------------------

def load_fabric_variables(variables_file: Path) -> Dict:
    with variables_file.open(encoding="utf-8") as handle:
        return json.load(handle)


def calculate_loopback_ip(prefix: str, loopback_id: int) -> str:
    network = ip_network(prefix)
    host = network.network_address + loopback_id
    return str(host)


def enrich_devices(fabric: Dict) -> Iterable[Dict]:
    devices = fabric["devices"]
    loopback_prefix = fabric["loopback_prefix"]
    index = {device["name"]: device for device in devices}
    used_vpc_domains = {}

    for device in devices:
        device["loopback_ip"] = calculate_loopback_ip(loopback_prefix, device["loopback_id"])

        if device["role"] == "spine":
            device["downlinks"] = [
                {
                    "name": peer["name"],
                    "ip": calculate_loopback_ip(loopback_prefix, peer["loopback_id"]),
                }
                for peer in devices
                if peer["role"] != "spine"
            ]

        if device.get("vpc"):
            peer_name = device["vpc"]["peer"]
            peer = index.get(peer_name)
            if not peer:
                raise ValueError(f"vPC peer {peer_name} for {device['name']} not found")

            domain_id = device["vpc"]["domain_id"]
            owners = used_vpc_domains.setdefault(domain_id, set())
            owners.add(device["name"])
            if len(owners) > 2:
                raise ValueError(
                    f"vPC domain {domain_id} used by more than two switches: {owners}"
                )

            device["vpc_peer_mgmt_ip"] = peer["mgmt_ip"]
            device["vpc_role_priority"] = 10 if device["name"].endswith("1") else 20

        yield device


# -----------------------------------------------------------------------------
# Rendering helper
# -----------------------------------------------------------------------------

def render_device_config(environment: Environment, fabric: Dict, device: Dict) -> str:
    template = environment.get_template("device_full_config.j2")
    return template.render(
        fabric_name=fabric["fabric_name"],
        multicast_group=fabric["multicast_group"],
        bgp_asn=fabric["bgp_asn"],
        evpn_rrs=fabric["evpn_rrs"],
        device=device,
    )


# -----------------------------------------------------------------------------
# Netmiko workflow
# -----------------------------------------------------------------------------

def connect_and_push(device: Dict, config: str, username: str, password: str) -> None:
    """Open an SSH session, preview the change, and commit on confirmation."""

    # Netmiko uses a dictionary of connection parameters. Keeping the mapping in
    # code helps beginners understand the expected keys and values.
    connection_params = {
        "device_type": "cisco_nxos",
        "host": device["mgmt_ip"],
        "username": username,
        "password": password,
        "fast_cli": False,
    }

    print(f"\nConnecting to {device['name']} ({device['mgmt_ip']}) ...")
    with ConnectHandler(**connection_params) as conn:
        print("Entering configuration session and loading candidate config ...")
        conn.config_mode()
        conn.send_config_set(config.splitlines(), enter_config_mode=False, exit_config_mode=False)

        print("\nProposed changes (show diff) ->")
        diff_output = conn.send_command("show diff")
        print(diff_output)

        apply = input("Commit changes to device? [yes/no]: ").strip().lower()
        if apply in {"yes", "y"}:
            print("Committing configuration ...")
            conn.exit_config_mode()
            conn.save_config()
            print("Configuration committed and saved.")
        else:
            print("Discarding staged configuration ...")
            conn.send_command_timing("abort", strip_prompt=False, strip_command=False)
            conn.exit_config_mode()
            print("Staged configuration removed. No changes were made.")


def main() -> None:
    variables_path = Path(__file__).with_name("fabric_variables.json")
    template_dir = Path(__file__).with_name("templates")

    fabric = load_fabric_variables(variables_path)
    environment = Environment(loader=FileSystemLoader(template_dir))

    username = input("Username: ")
    password = getpass("Password: ")

    for device in enrich_devices(fabric):
        config = render_device_config(environment, fabric, device)
        connect_and_push(device, config, username, password)


if __name__ == "__main__":
    main()
