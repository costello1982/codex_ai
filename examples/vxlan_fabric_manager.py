"""High-level VXLAN EVPN fabric manager.

This module complements ``basic_vxlan_conf.py`` by adding:

* service definitions (VRFs/VLANs/VNIs) that can be layered on top of the
  baseline underlay deployment
* parallel configuration pushes with robust exception handling
* inventory loading from YAML/JSON to support production workflows

Usage tips:
    python vxlan_fabric_manager.py --inventory fabric.yml --services services.yml

Both files are optional.  When omitted, the script falls back to the same sample
inventory defined in ``basic_vxlan_conf`` so that you can experiment without
needing any external data sources.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Iterable, List, Optional

import yaml

from basic_vxlan_conf import Device, DeviceRole, VXLANConfigurator

# ---------------------------------------------------------------------------
# Service definition models
# ---------------------------------------------------------------------------


@dataclass
class VRFService:
    """Describes a tenant VRF."""

    name: str
    vni: int
    route_distinguisher: str
    export_rt: str
    import_rt: str


@dataclass
class VLANService:
    """Describes a VLAN/VNI bridge domain."""

    vlan_id: int
    vni: int
    description: str
    vrf: str


@dataclass
class ServiceBundle:
    """Collection of overlay services to deploy on a set of leaves."""

    vrfs: List[VRFService]
    vlans: List[VLANService]
    target_roles: List[DeviceRole]


# ---------------------------------------------------------------------------
# Overlay extension logic
# ---------------------------------------------------------------------------


class ServiceAwareConfigurator(VXLANConfigurator):
    """Extends the baseline configurator with overlay services."""

    def __init__(
        self,
        devices: Iterable[Device],
        services: Optional[ServiceBundle] = None,
        fabric_name: str = "DC1",
    ) -> None:
        super().__init__(list(devices), fabric_name=fabric_name)
        self.services = services

    def build_overlay_config(self, device: Device) -> List[str]:  # type: ignore[override]
        base_commands = super().build_overlay_config(device)
        if not self.services or device.role not in self.services.target_roles:
            return base_commands

        commands = list(base_commands)
        commands.extend(self._vrf_overlay(device))
        commands.extend(self._vlan_overlay(device))
        return commands

    def _vrf_overlay(self, device: Device) -> List[str]:
        commands: List[str] = []
        for vrf in self.services.vrfs:
            commands.extend(
                [
                    f"vrf context {vrf.name}",
                    f"  rd {vrf.route_distinguisher}",
                    f"  address-family ipv4 unicast",
                    f"    route-target both {vrf.export_rt}",
                    f"    route-target both {vrf.import_rt}",
                    "    redistribute connected",
                    "  exit",
                    "exit",
                    "router bgp 65000",
                    "  address-family ipv4 unicast",
                    f"    vrf {vrf.name}",
                    "      advertise l2vpn evpn",
                    "    exit",
                    "  exit",
                    "exit",
                ]
            )
        return commands

    def _vlan_overlay(self, device: Device) -> List[str]:
        commands: List[str] = []
        for vlan in self.services.vlans:
            commands.extend(
                [
                    f"vlan {vlan.vlan_id}",
                    f"  name {vlan.description}",
                    "exit",
                    f"vlan configuration {vlan.vlan_id}",
                    f"  member vni {vlan.vni}",
                    "exit",
                    f"interface nve1",
                    f"  member vni {vlan.vni}",
                    "    suppress-arp",
                    "    ingress-replication protocol bgp",
                    "  exit",
                    "exit",
                    f"interface vlan {vlan.vlan_id}",
                    f"  description {vlan.description}",
                    f"  vrf member {vlan.vrf}",
                    "  no shutdown",
                    "exit",
                ]
            )
        return commands


# ---------------------------------------------------------------------------
# Inventory parsing helpers
# ---------------------------------------------------------------------------


def load_devices_from_file(path: Optional[Path]) -> List[Device]:
    if not path:
        return []

    if path.suffix in {".yml", ".yaml"}:
        data = yaml.safe_load(path.read_text())
    elif path.suffix == ".json":
        data = json.loads(path.read_text())
    else:
        raise ValueError("Unsupported inventory format. Use YAML or JSON.")

    devices = []
    for entry in data.get("devices", []):
        devices.append(
            Device(
                name=entry["name"],
                role=DeviceRole(entry["role"]),
                host=entry["host"],
                loopback_base=entry.get("loopback_base", data.get("loopback_base", "10.255.0.0/24")),
                vpc_pair=entry.get("vpc_pair"),
                asn=entry.get("asn"),
                tags=tuple(entry.get("tags", [])),
                metadata=entry.get("metadata", {}),
            )
        )
    return devices


def load_services_from_file(path: Optional[Path]) -> Optional[ServiceBundle]:
    if not path:
        return None

    data = yaml.safe_load(path.read_text())
    vrfs = [
        VRFService(
            name=entry["name"],
            vni=entry["vni"],
            route_distinguisher=entry["rd"],
            export_rt=entry["export_rt"],
            import_rt=entry["import_rt"],
        )
        for entry in data.get("vrfs", [])
    ]
    vlans = [
        VLANService(
            vlan_id=entry["vlan_id"],
            vni=entry["vni"],
            description=entry.get("description", f"VLAN{entry['vlan_id']}"),
            vrf=entry["vrf"],
        )
        for entry in data.get("vlans", [])
    ]
    target_roles = [DeviceRole(role) for role in data.get("target_roles", ["leaf", "border_leaf"])]
    return ServiceBundle(vrfs=vrfs, vlans=vlans, target_roles=target_roles)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy VXLAN EVPN services")
    parser.add_argument("--inventory", type=Path, help="Path to YAML/JSON inventory", default=None)
    parser.add_argument("--services", type=Path, help="Path to services YAML", default=None)
    parser.add_argument("--fabric-name", default="DC1")
    args = parser.parse_args()

    devices = load_devices_from_file(args.inventory)
    if not devices:
        from basic_vxlan_conf import build_sample_inventory

        loopback_subnet = input("Loopback supernet for automation [10.255.0.0/24]: ").strip() or "10.255.0.0/24"
        devices = build_sample_inventory(loopback_subnet)

    services = load_services_from_file(args.services)
    configurator = ServiceAwareConfigurator(devices, services=services, fabric_name=args.fabric_name)

    username = input("Username: ")
    password = getpass("Password: ")

    print("Starting deployment...\n")
    with ThreadPoolExecutor(max_workers=min(8, len(configurator.devices))) as executor:
        future_map = {
            executor.submit(configurator.push_config, device, username, password): device
            for device in configurator.devices
        }

        for future in as_completed(future_map):
            device = future_map[future]
            try:
                future.result()
                print(f"✔ Successfully configured {device.name}")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"✖ Failed to configure {device.name}: {exc}")


if __name__ == "__main__":
    main()
