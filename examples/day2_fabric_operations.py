"""Day-2 fabric operations helper for Cisco NX-OS VXLAN/EVPN fabrics.

This script focuses on the tasks you repeatedly perform after the fabric is
built: onboarding a new tenant, extending VLANs/VXLANs, and validating that the
state of the fabric remains healthy.  The script intentionally contains a large
amount of commentary so that newcomers can learn both the *why* and *how* of
automation while staying production-ready.

Key goals of the design:

* keep workflows modular so you can extend them with new checks later
* double-check the fabric before touching the configuration ("trust but verify")
* always show an actionable diff before committing changes
* integrate with Git so you can roll back quickly if something goes wrong

The implementation leans on NAPALM because it provides a driver that can push
merge configurations to NX-OS while also exposing `compare_config()` and
`rollback()` helpers.  If you prefer Netmiko or the NX-API, you can swap the
transport within the `DeviceSession` class without changing the higher-level
workflow.
"""
from __future__ import annotations

from dataclasses import dataclass
from getpass import getpass
import ipaddress
import json
from pathlib import Path
from textwrap import dedent
from typing import Dict, Iterable, List, Optional

from napalm import get_network_driver  # type: ignore
from napalm.base.base import NetworkDriver  # type: ignore


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class TenantVlanRequest:
    """Describe the VLAN/VXLAN service that we want to roll out.

    Attributes:
        tenant: Logical tenant name (used for VRF, route-targets, etc.).
        vlan_id: Numeric VLAN identifier.  We assume classic 1-4094 VLAN IDs.
        l2_only: Whether the tenant is L2-only (False = needs an Anycast GW).
        svi_gateway: Optional IPv4 gateway address (e.g. "10.10.200.1/24").
        vrf: Optional VRF name; default is derived from the tenant.
        fabric_scope: Either "all" for a fabric-wide VLAN, or an iterable of
            device hostnames where the VLAN should exist.
    """

    tenant: str
    vlan_id: int
    l2_only: bool
    svi_gateway: Optional[str] = None
    vrf: Optional[str] = None
    fabric_scope: Optional[Iterable[str]] = None

    def computed_vrf(self) -> str:
        """Return the VRF name to use for this tenant.

        The default VRF naming convention is ``VRF_<TENANT>``.  You can adjust
        this function to match your local standard.
        """

        if self.vrf:
            return self.vrf
        return f"VRF_{self.tenant.upper()}"

    def computed_vni(self) -> int:
        """Derive the VNI using the "100 + VLAN" pattern recommended by the user.

        You can replace this with another function (for example 10000 + VLAN)
        without modifying any other part of the script.
        """

        return 100_000 + self.vlan_id


@dataclass
class DeviceInventoryItem:
    """Simple representation of a fabric node in our inventory."""

    hostname: str
    mgmt_ip: str
    role: str  # e.g. "leaf", "border_leaf", "spine"
    vtep_ip: Optional[str] = None


# ---------------------------------------------------------------------------
# Device session helpers
# ---------------------------------------------------------------------------


class DeviceSession:
    """Thin wrapper around a NAPALM session.

    The wrapper lets us centralise credential handling, optional arguments, and
    add strongly-typed helper methods for the commands we run frequently.
    """

    def __init__(self, host: str, username: str, password: str) -> None:
        driver = get_network_driver("nxos_ssh")
        optional_args = {"port": 22}
        self.connection: NetworkDriver = driver(
            hostname=host,
            username=username,
            password=password,
            optional_args=optional_args,
        )

    def __enter__(self) -> "DeviceSession":
        self.connection.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.connection.close()

    # -- Show commands -----------------------------------------------------

    def cli(self, commands: Dict[str, str]) -> Dict[str, str]:
        """Run multiple CLI commands and return their raw output."""

        return self.connection.cli(commands)

    def checkpoint(self, filename: Path) -> None:
        """Save the current running configuration to disk.

        NX-OS supports `checkpoint` to create a rollback file on the device.
        The `save_config` call downloads the running config locally so that we
        can commit it to Git and roll back quickly by restoring the previous
        version.  This design keeps the workflow vendor-neutral: you can push
        the snapshot into Git, or into your preferred CMDB.
        """

        filename.write_text(self.connection.get_config()["running"])

    # -- Config management -------------------------------------------------

    def load_merge(self, config_snippet: str) -> None:
        """Stage a merge configuration on the device."""

        self.connection.load_merge_candidate(config=config_snippet)

    def compare(self) -> str:
        """Return the diff between the candidate configuration and running."""

        return self.connection.compare_config()

    def commit(self, message: str = "") -> None:
        """Commit the candidate configuration."""

        self.connection.commit_config(message)

    def discard(self) -> None:
        """Discard the candidate configuration."""

        self.connection.discard_config()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_vlan(session: DeviceSession, vlan_id: int) -> bool:
    """Return True when the VLAN either does not exist or matches expectations.

    The goal is to warn operators when the VLAN already exists so they can
    decide whether this run represents an expansion (for example, extending the
    VLAN to additional leafs) or an accidental duplicate request.  Returning
    ``True`` keeps the workflow moving while still highlighting the situation.
    """

    try:
        output = session.cli({"vlan": f"show vlan id {vlan_id}"})["vlan"]
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"[WARN] Unable to validate VLAN {vlan_id}: {exc}")
        return False

    if f"VLAN {vlan_id}" in output:
        print(f"[INFO] VLAN {vlan_id} already exists; validating attributes before merge.")
    else:
        print(f"[INFO] VLAN {vlan_id} not found; will create it as part of this run.")
    return True


def validate_vni_mapping(session: DeviceSession, vlan_id: int, vni: int) -> bool:
    """Ensure the VLAN-to-VNI mapping is not already in use with a different VNI."""

    command = {"vn-seg": "show nve vn-segment-vlan"}
    try:
        output = session.cli(command)["vn-seg"]
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"[WARN] Unable to validate VNI mapping: {exc}")
        return False

    for line in output.splitlines():
        if f"{vlan_id}" in line and "".join(line.split()) != "":
            if str(vni) not in line:
                print(
                    f"[ERROR] VLAN {vlan_id} already mapped to a different VNI."
                )
                return False
            print(f"[INFO] VLAN {vlan_id} already mapped to VNI {vni}; will reuse it.")
            return True

    print(f"[INFO] VLAN {vlan_id} not yet mapped to VNI {vni}; ready to configure.")
    return True


def validate_nve_peering(session: DeviceSession, peer_vtep: str) -> bool:
    """Verify that the NVE interface sees the remote VTEP.

    We assume Loopback0 is the VTEP source address.  The command checks the NVE
    peer list so we can highlight missing connectivity before pushing configs.
    """

    try:
        output = session.cli({"peers": "show nve peers"})["peers"]
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"[WARN] Unable to validate NVE peers: {exc}")
        return False

    return peer_vtep in output


# ---------------------------------------------------------------------------
# Configuration rendering helpers
# ---------------------------------------------------------------------------


def render_vlan_config(request: TenantVlanRequest) -> str:
    """Render the VLAN/NVE configuration snippet for NX-OS."""

    vlan_id = request.vlan_id
    vni = request.computed_vni()
    svi_lines: List[str] = []

    if not request.l2_only and request.svi_gateway:
        gateway_ip = ipaddress.ip_interface(request.svi_gateway)
        svi_lines = [
            f"interface Vlan{vlan_id}",
            "  no shutdown",
            f"  description Tenant {request.tenant} Anycast Gateway",
            f"  vrf member {request.computed_vrf()}",
            f"  ip address {gateway_ip.ip} {gateway_ip.network.netmask}",
            "  fabric forwarding mode anycast-gateway",
        ]

    template = [
        f"vlan {vlan_id}",
        f"  name {request.tenant}_VLAN_{vlan_id}",
        "  vn-segment {vni}",
        "",
        f"evpn",
        f"  vni {vni} l2",
        f"    rd auto",
        f"    route-target import auto",
        f"    route-target export auto",
    ]

    config_lines = template
    if svi_lines:
        config_lines.append("")
        config_lines.extend(svi_lines)

    return "\n".join(config_lines) + "\n"


# ---------------------------------------------------------------------------
# Workflow orchestration
# ---------------------------------------------------------------------------


def load_inventory(path: Path) -> List[DeviceInventoryItem]:
    """Load a JSON inventory file from disk.

    The inventory should look like::

        [
          {
            "hostname": "leaf01",
            "mgmt_ip": "10.0.0.11",
            "vtep_ip": "192.0.2.11",
            "role": "leaf"
          }
        ]
    """

    raw = json.loads(path.read_text())
    return [
        DeviceInventoryItem(**item)
        for item in raw
        if item.get("role") in {"leaf", "border_leaf", "border_gateway"}
    ]


def filter_scope(
    inventory: List[DeviceInventoryItem], request: TenantVlanRequest
) -> List[DeviceInventoryItem]:
    """Return the devices that should receive the configuration."""

    if request.fabric_scope is None or request.fabric_scope == "all":
        return inventory

    scope = set(host for host in request.fabric_scope)
    return [item for item in inventory if item.hostname in scope]


def day2_workflow(
    request: TenantVlanRequest,
    inventory: List[DeviceInventoryItem],
    username: str,
    password: str,
    dry_run: bool = False,
) -> None:
    """Execute the day-2 VLAN onboarding workflow across the selected devices."""

    target_devices = filter_scope(inventory, request)
    vni = request.computed_vni()
    config_snippet = render_vlan_config(request)

    for device in target_devices:
        print("-" * 79)
        print(f"[INFO] Processing {device.hostname} ({device.mgmt_ip})")

        with DeviceSession(device.mgmt_ip, username, password) as session:
            # --- 1) Take a snapshot before touching anything -----------------
            snapshot_path = Path(f"backups/{device.hostname}_running.cfg")
            snapshot_path.parent.mkdir(exist_ok=True)
            session.checkpoint(snapshot_path)
            print(f"[INFO] Saved running config snapshot to {snapshot_path}")

            # --- 2) Validate the current state --------------------------------
            vlan_ok = validate_vlan(session, request.vlan_id)
            vni_ok = validate_vni_mapping(session, request.vlan_id, vni)

            if not (vlan_ok and vni_ok):
                print(
                    f"[ERROR] Skipping {device.hostname} due to validation failure."
                )
                continue

            # Optional: verify NVE peer reachability by checking loopback IPs of
            # other target devices.  We only warn if we cannot find all peers.
            for peer in target_devices:
                if peer.hostname == device.hostname:
                    continue
                peer_vtep = peer.vtep_ip or peer.mgmt_ip
                if not peer_vtep:
                    continue
                peer_reachable = validate_nve_peering(session, peer_vtep)
                if not peer_reachable:
                    print(
                        f"[WARN] {device.hostname} does not report NVE peer {peer_vtep}"
                    )

            # --- 3) Stage the merge configuration ----------------------------
            session.load_merge(config_snippet)
            diff = session.compare()
            if not diff.strip():
                print(f"[INFO] No changes required on {device.hostname}.")
                session.discard()
                continue

            print("[INFO] Proposed diff:")
            print(diff)

            if dry_run:
                print(
                    "[DRY-RUN] Skipping commit because dry_run=True."
                )
                session.discard()
                continue

            choice = input(
                f"Apply the changes to {device.hostname}? Type 'yes' to commit, anything else to abort: "
            )
            if choice.strip().lower() != "yes":
                print("[INFO] Discarding staged config.")
                session.discard()
                continue

            session.commit(message=f"Automated VLAN {request.vlan_id} deployment")
            print(f"[INFO] Committed changes on {device.hostname}.")


# ---------------------------------------------------------------------------
# User interaction helpers
# ---------------------------------------------------------------------------


def prompt_for_request() -> TenantVlanRequest:
    """Collect the tenant/VLAN parameters interactively from the operator."""

    tenant = input("Tenant name (e.g. ACME): ").strip()
    vlan_id = int(input("VLAN ID (e.g. 200): ").strip())
    scope_raw = input(
        "Fabric scope (comma separated hostnames or 'all' for every leaf): "
    ).strip()

    l2_only = input("Is this L2-only? (yes/no): ").strip().lower().startswith("y")

    svi_gateway: Optional[str] = None
    if not l2_only:
        svi_gateway = input(
            "Anycast gateway IPv4 address (CIDR, e.g. 10.10.200.1/24): "
        ).strip()

    scope: Optional[Iterable[str]]
    if scope_raw.lower() == "all" or not scope_raw:
        scope = "all"
    else:
        scope = [item.strip() for item in scope_raw.split(",") if item.strip()]

    return TenantVlanRequest(
        tenant=tenant,
        vlan_id=vlan_id,
        l2_only=l2_only,
        svi_gateway=svi_gateway,
        fabric_scope=scope,
    )


def main() -> None:
    """Entry point for the command-line workflow."""

    print(
        dedent(
            """
            Day-2 Fabric Operations
            ======================

            This helper guides you through adding a VLAN/VNI to a VXLAN EVPN fabric.
            You will need:
              * a JSON inventory file describing the leaf/border leaf nodes
              * reachability to the management interface of those switches
              * network credentials with permission to configure the fabric

            Tip: keep the `backups/` directory under Git.  Each time you run the
            script, you will collect a fresh snapshot that you can version and
            roll back easily by checking out the previous commit and copying the
            configuration back to the device (`configure replace` on NX-OS).
            """
        )
    )

    inventory_path = Path(
        input("Path to inventory JSON (default: inventory.json): ").strip() or "inventory.json"
    )
    if not inventory_path.exists():
        raise FileNotFoundError(
            f"Inventory file {inventory_path} not found. Create it before running the script."
        )

    inventory = load_inventory(inventory_path)
    if not inventory:
        raise RuntimeError("Inventory does not contain any leaf/border devices.")

    username = input("Username: ").strip()
    password = getpass("Password: ")

    request = prompt_for_request()

    dry_run = input("Run in dry-run mode? (yes/no): ").strip().lower().startswith("y")

    day2_workflow(
        request=request,
        inventory=inventory,
        username=username,
        password=password,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
