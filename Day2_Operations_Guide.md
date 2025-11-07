# Day-2 Operations Playbook for NX-OS VXLAN Fabrics

This playbook accompanies `examples/day2_fabric_operations.py` and shows how to
extend a production VXLAN EVPN fabric safely.  The intent is to teach a repeat-
able process that combines automated validation, staged configuration merges,
and version-controlled backups so you can scale tenant onboarding without
surprises.

## When to Use This Workflow

* **Onboard a new tenant VLAN/VNI** across the entire fabric or a subset of
  leaf/border-leaf switches.
* **Extend an existing VLAN** to additional access ports while reusing the same
  Anycast Gateway and VNI mapping.
* **Audit the current state** to confirm that VXLAN components (VLAN database,
  VLAN-to-VNI mappings, and NVE peers) are aligned before you touch the config.

## Inventory and Data Model

The script expects a JSON inventory that lists every leaf/border device you may
touch.  Each entry provides the management IP (used for SSH/NAPALM access), the
fabric role, and optionally the loopback/VTEP address so that NVE peering can be
validated.

```json
[
  {
    "hostname": "leaf01",
    "mgmt_ip": "10.0.0.11",
    "vtep_ip": "192.0.2.11",
    "role": "leaf"
  },
  {
    "hostname": "leaf02",
    "mgmt_ip": "10.0.0.12",
    "vtep_ip": "192.0.2.12",
    "role": "leaf"
  }
]
```

You can maintain this inventory in Git alongside the script so every change is
reviewed and documented.

## VNI Allocation Strategy

*The script defaults to `VNI = 100000 + VLAN_ID`*, matching the user's request
for values such as `VLAN 200 → VNI 100200`.  The helper is easy to customise if
your environment prefers a different formula (for example, `500000 + VLAN`).

Best practices:

1. **Keep VLAN/VNI IDs globally unique** to simplify operations and EVPN
   troubleshooting.
2. **Document the scheme** in your engineering standards so other engineers know
   how to pre-allocate ranges for tenants.

## Fabric Scope Decisions

Many operations engineers debate whether to create VLANs everywhere or only on
switches that host endpoints.  With EVPN, the control plane handles advertising
MAC/IP reachability, so either model works:

* **Fabric-wide VLANs** simplify automation and guarantee consistency but can
  clutter the VLAN database when you have thousands of services.
* **Scoped VLANs** (the default in the script) reduce the blast radius.  The
  tool prompts you for a comma-separated list of switches so you can target only
  the leafs that host the workload.

You can change the default to "all" if you prefer ubiquitous VLAN creation.

## Pre-Change Validation

Before staging configuration, the script checks:

* **`show vlan id <ID>`** — warns you if the VLAN already exists so you can
  confirm that the change is an extension rather than a duplicate.
* **`show nve vn-segment-vlan`** — verifies that the VLAN-to-VNI mapping matches
  the expected value or is free.
* **`show nve peers`** — ensures each target device reports its fellow VTEPs.

If any validation fails, the device is skipped and clearly logged so you can fix
the issue manually before re-running the automation.

## Configuration Generation and Diff Review

The configuration renderer builds the minimum viable snippet:

* `vlan <ID>` with name and `vn-segment <VNI>`
* `evpn` section with `vni <VNI> l2`
* Optional Anycast Gateway configuration on the SVI when the tenant is L3-aware

NAPALM stages the snippet as a merge candidate so you can run `compare_config()`
and see the delta before committing.  Nothing is pushed without an explicit
"yes" from the operator unless you intentionally run in `--dry-run` mode.

## Backups and Rollback

Every execution saves the running configuration to `backups/<hostname>`.  Track
that directory in Git and commit snapshots after successful changes.  Rollback
is as simple as checking out the previous commit and using `configure replace`
or `load replace` with the saved file.

For emergency recovery, NAPALM also supports `discard_config()` (used when you
cancel) and `rollback()` if you would rather rely on device-native checkpoints.

## Extending the Script

The module is heavily commented so you can add new day-2 tasks:

* Extend the `TenantVlanRequest` dataclass with DHCP relay, multicast, or QoS
  attributes.
* Add new validation helpers (for example, checking interface descriptions or
  verifying that access ports are in the correct mode).
* Integrate with a source of truth such as NetBox or Nautobot by replacing the
  JSON loader with their APIs.

Always enhance the automated checks first—config pushes should be the last step
once the fabric is confirmed healthy.
