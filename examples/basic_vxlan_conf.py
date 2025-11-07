"""Basic VXLAN EVPN configuration workflow for Cisco NX-OS fabrics.

This script demonstrates a production-ready pattern for generating and pushing
baseline VXLAN/EVPN configurations for fabrics composed of spines, leaves,
border leaves, and border gateways.  The goals of the design are:

* keep the workflow modular and easy to extend with new features
* avoid accidental configuration drift such as duplicated vPC domain IDs
* provide extensive commentary so new automation engineers can follow along
* offer an opinionated starting point that you can adapt to your environment

The script focuses on three major sections of a brownfield/greenfield bring-up:

1. Feature enablement (``feature nv overlay`` and friends)
2. Underlay configuration (loopback interfaces, PIM/ISIS/BGP underlay, etc.)
3. Overlay configuration (NVE interface, VLAN-to-VNI mappings, EVPN services)

The script expects ``netmiko`` to be installed so that it can open CLI sessions
to Nexus platforms over SSH.  You can install it with ``pip install netmiko``.
The configuration snippets are intentionally simplified yet production-ready and
can easily be expanded by editing the helper methods in ``VXLANConfigurator``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from getpass import getpass
import ipaddress
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from netmiko import ConnectHandler  # type: ignore
from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException  # type: ignore

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class DeviceRole(str, Enum):
    """Roles that exist in a typical VXLAN EVPN fabric."""

    SPINE = "spine"
    LEAF = "leaf"
    BORDER_LEAF = "border_leaf"
    BORDER_GATEWAY = "border_gateway"


@dataclass
class Device:
    """Represents a fabric node and its automation metadata."""

    name: str
    role: DeviceRole
    host: str
    loopback_base: str
    vpc_pair: Optional[str] = None
    asn: Optional[int] = None
    tags: Tuple[str, ...] = ()
    metadata: Dict[str, str] = field(default_factory=dict)

    def loopback_ip(self) -> str:
        """Return a deterministic loopback IP derived from the device name and role."""
        base_network = ipaddress.ip_network(self.loopback_base)

        # Extract numeric suffix from device name.  If no explicit digits are present,
        # we fall back to the last octet in order of appearance to keep the logic safe.
        suffix_digits = "".join(ch for ch in self.name if ch.isdigit())
        suffix = int(suffix_digits) if suffix_digits else 1

        role_offset = {
            DeviceRole.LEAF: 0,
            DeviceRole.SPINE: 50,
            DeviceRole.BORDER_LEAF: 100,
            DeviceRole.BORDER_GATEWAY: 200,
        }[self.role]

        host_id = suffix + role_offset
        # Guard against generating an IP outside of the provided subnet.
        if host_id >= base_network.num_addresses:
            raise ValueError(
                f"Loopback subnet {self.loopback_base} too small for host id {host_id}"
            )

        ip_address = base_network[host_id]
        return str(ip_address)


# ---------------------------------------------------------------------------
# Configuration builder
# ---------------------------------------------------------------------------


class VXLANConfigurator:
    """Generate and push VXLAN EVPN configurations for a fabric."""

    def __init__(self, devices: Sequence[Device], fabric_name: str = "DC1") -> None:
        self.devices = list(devices)
        self.fabric_name = fabric_name
        self.vpc_domain_registry: Dict[str, int] = {}

    # ----------------------------
    # Feature configuration
    # ----------------------------
    def build_feature_config(self, device: Device) -> List[str]:
        """Return feature enablement commands specific to the device."""
        commands = [
            "terminal dont-ask",
            "feature nv overlay",
            "feature ospf",  # Replace with ISIS/BGP as required
            "feature bgp",
            "feature pim",
            "feature lacp",
        ]

        # Enable NDFC compatibility or fabric automation tags if needed.
        if "ndfc-managed" in device.tags:
            commands.append("feature ndp")
        return commands

    # ----------------------------
    # Underlay configuration
    # ----------------------------
    def build_underlay_config(self, device: Device) -> List[str]:
        """Return underlay commands such as loopbacks, routing, and PIM."""
        loopback_ip = device.loopback_ip()
        commands = [
            f"interface loopback0",
            "  description Fabric-Loopback",
            f"  ip address {loopback_ip}/32",
            "  ip router ospf UNDERLAY area 0.0.0.0",
            "exit",
            "router ospf UNDERLAY",
            f"  router-id {loopback_ip}",
            "  passive-interface default",
            "exit",
        ]

        if device.role in {DeviceRole.LEAF, DeviceRole.BORDER_LEAF, DeviceRole.BORDER_GATEWAY}:
            commands.extend(self._build_vpc_commands(device))
        return commands

    def _build_vpc_commands(self, device: Device) -> List[str]:
        """Construct vPC configuration for nodes that participate in pairs."""
        if not device.vpc_pair:
            # Leaves not running vPC (e.g., single-attached) skip this section.
            return []

        domain_id = self._allocate_vpc_domain(device.vpc_pair)
        peer_link = device.metadata.get("peer_link", "port-channel10")
        keepalive = device.metadata.get("keepalive_src", device.loopback_ip())
        keepalive_dest = device.metadata.get("keepalive_dest")

        if not keepalive_dest:
            raise ValueError(
                f"Missing keepalive destination for {device.name}. Add 'keepalive_dest' metadata."
            )

        commands = [
            f"vpc domain {domain_id}",
            f"  role priority {10 if 'primary' in device.tags else 20}",
            f"  peer-keepalive destination {keepalive_dest} source {keepalive} vrf management",
            "  peer-switch",
            f"interface {peer_link}",
            "  switchport",
            "  switchport mode trunk",
            "  spanning-tree port type network",
            "  vpc peer-link",
            "exit",
        ]
        return commands

    def _allocate_vpc_domain(self, pair_name: str) -> int:
        """Ensure a unique vPC domain for each pair and return it."""
        if pair_name in self.vpc_domain_registry:
            return self.vpc_domain_registry[pair_name]

        base_id = 10 + len(self.vpc_domain_registry) * 10
        if base_id in self.vpc_domain_registry.values():
            raise RuntimeError("vPC domain collision detected; adjust base allocation policy")
        self.vpc_domain_registry[pair_name] = base_id
        return base_id

    # ----------------------------
    # Overlay configuration
    # ----------------------------
    def build_overlay_config(self, device: Device) -> List[str]:
        """Construct overlay/NVE commands."""
        loopback_ip = device.loopback_ip()
        commands = [
            "interface nve1",
            "  no shutdown",
            f"  source-interface loopback0",
            "  host-reachability protocol bgp",
            "exit",
            "router bgp 65000",
            f"  router-id {loopback_ip}",
            "  address-family l2vpn evpn",
            "    retain route-target all",
            "  exit",
            "exit",
        ]

        if device.role in {DeviceRole.BORDER_LEAF, DeviceRole.BORDER_GATEWAY}:
            commands.extend(
                [
                    "  address-family ipv4 unicast",
                    "    redistribute connected",
                    "  exit",
                ]
            )
        return commands

    # ----------------------------
    # Orchestration helpers
    # ----------------------------
    def device_config(self, device: Device) -> List[str]:
        """Return the full ordered configuration for a device."""
        config: List[str] = []
        config.extend(self.build_feature_config(device))
        config.extend(self.build_underlay_config(device))
        config.extend(self.build_overlay_config(device))
        return config

    def push_config(self, device: Device, username: str, password: str) -> None:
        """Connect to the device and push the generated configuration."""
        connection_params = {
            "device_type": "cisco_nxos",
            "host": device.host,
            "username": username,
            "password": password,
            "session_log": f"logs/{device.name}.log",
        }

        Path("logs").mkdir(exist_ok=True)

        commands = self.device_config(device)
        try:
            with ConnectHandler(**connection_params) as conn:
                conn.send_config_set(commands)
                conn.save_config()
        except NetmikoAuthenticationException as exc:
            raise RuntimeError(f"Authentication failed for {device.name}: {exc}") from exc
        except NetmikoTimeoutException as exc:
            raise RuntimeError(f"Timed out connecting to {device.name}: {exc}") from exc

    def deploy(self, username: str, password: str) -> None:
        """Push configuration to all devices sequentially."""
        for device in self.devices:
            print(f"\n--- Deploying to {device.name} ({device.role}) ---")
            commands = self.device_config(device)
            print("Preview configuration:")
            for line in commands:
                print(f"  {line}")

            confirmation = input("Apply this configuration? [y/N]: ").strip().lower()
            if confirmation != "y":
                print(f"Skipping {device.name} at user request.")
                continue

            self.push_config(device, username, password)
            print(f"Configuration pushed successfully to {device.name}.")


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

def build_sample_inventory(loopback_subnet: str) -> List[Device]:
    """Return an inventory tailored to a dual-spine/leaf fabric."""
    return [
        Device(
            name="spine01",
            role=DeviceRole.SPINE,
            host="198.18.1.11",
            loopback_base=loopback_subnet,
            asn=65010,
        ),
        Device(
            name="spine02",
            role=DeviceRole.SPINE,
            host="198.18.1.12",
            loopback_base=loopback_subnet,
            asn=65010,
        ),
        Device(
            name="leaf01",
            role=DeviceRole.LEAF,
            host="198.18.2.21",
            loopback_base=loopback_subnet,
            vpc_pair="leaf_pair_1",
            tags=("primary",),
            metadata={"keepalive_dest": "198.18.2.22"},
        ),
        Device(
            name="leaf02",
            role=DeviceRole.LEAF,
            host="198.18.2.22",
            loopback_base=loopback_subnet,
            vpc_pair="leaf_pair_1",
            metadata={"keepalive_dest": "198.18.2.21"},
        ),
        Device(
            name="border_leaf01",
            role=DeviceRole.BORDER_LEAF,
            host="198.18.3.31",
            loopback_base=loopback_subnet,
            vpc_pair="border_leaf_pair",
            tags=("primary",),
            metadata={"keepalive_dest": "198.18.3.32"},
        ),
        Device(
            name="border_leaf02",
            role=DeviceRole.BORDER_LEAF,
            host="198.18.3.32",
            loopback_base=loopback_subnet,
            vpc_pair="border_leaf_pair",
            metadata={"keepalive_dest": "198.18.3.31"},
        ),
        Device(
            name="border_gateway01",
            role=DeviceRole.BORDER_GATEWAY,
            host="198.18.3.41",
            loopback_base=loopback_subnet,
        ),
    ]


def main() -> None:
    """Entry point when executing the script directly."""
    fabric_name = input("Fabric name [DC1]: ").strip() or "DC1"
    loopback_subnet = input("Loopback supernet for automation [10.255.0.0/24]: ").strip() or "10.255.0.0/24"

    inventory = build_sample_inventory(loopback_subnet)
    configurator = VXLANConfigurator(inventory, fabric_name=fabric_name)

    username = input("Username: ")
    password = getpass("Password: ")

    configurator.deploy(username, password)


if __name__ == "__main__":
    main()
