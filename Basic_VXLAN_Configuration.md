# Basic VXLAN Configuration Workflow

This guide explains how to use the sample automation scripts that accompany this
repository to deploy a baseline Cisco NX-OS VXLAN EVPN fabric.  The scripts live
under `examples/` and are intentionally designed to be easy to customize.

## Overview of the scripts

| Script | Purpose |
| --- | --- |
| `examples/basic_vxlan_conf.py` | Generates feature, underlay, and overlay configuration for spines, leaves, border leaves, and border gateways.  Prompts for credentials and applies the configuration sequentially, asking for confirmation per device. |
| `examples/vxlan_fabric_manager.py` | Builds on the basic script with optional YAML/JSON inventory parsing, service bundles (VRFs/VLANs/VNIs), and concurrent configuration pushes. |

Both scripts share the same data models so you can evolve from the basic sample
to the manager as your fabric grows.

## Prerequisites

1. Python 3.9+
2. Install dependencies:
   ```bash
   pip install netmiko pyyaml
   ```
3. Ensure SSH reachability to each NX-OS switch from the automation host.
4. Create a `logs/` directory or allow the scripts to do so automatically.

## Running `basic_vxlan_conf.py`

1. Inspect the sample inventory in the `build_sample_inventory` function to see
   how roles, vPC pairs, and loopback subnet automation are defined.
2. Execute the script:
   ```bash
   python examples/basic_vxlan_conf.py
   ```
3. When prompted, provide:
   - Fabric name (used for logging/context only)
   - Loopback supernet (e.g. `10.255.0.0/24`)
   - NX-OS username and password
4. The script previews the configuration for each device and requests
   confirmation before applying it via SSH.

### Loopback allocation logic

* Leaves use the numerical suffix from their hostname (e.g. `leaf01` → host id 1).
* Border leaves add an offset of 100 (e.g. `border_leaf01` → host id 101).
* Border gateways add an offset of 200.
* Spines add an offset of 50 to keep their addresses in a distinct range.

Adjust the offsets inside `Device.loopback_ip` if you need different spacing.

### vPC domain protection

The configurator automatically assigns unique vPC domain IDs per pair starting
at 10 and incrementing by 10.  If the automation encounters a collision it
raises a descriptive exception so that you can adjust the policy.

## Running `vxlan_fabric_manager.py`

This script extends the baseline workflow with inventory/service files and
parallel pushes.

1. Optionally create an inventory file (`fabric.yml`):
   ```yaml
   loopback_base: 10.255.0.0/24
   devices:
     - name: leaf01
       role: leaf
       host: 192.0.2.101
       vpc_pair: leaf_pair_1
       metadata:
         keepalive_dest: 192.0.2.102
       tags: [primary]
     - name: leaf02
       role: leaf
       host: 192.0.2.102
       vpc_pair: leaf_pair_1
       metadata:
         keepalive_dest: 192.0.2.101
   ```
2. Optionally define overlay services (`services.yml`):
   ```yaml
   target_roles: [leaf, border_leaf]
   vrfs:
     - name: Tenant-A
       vni: 10010
       rd: 65000:10
       export_rt: 65000:10
       import_rt: 65000:10
   vlans:
     - vlan_id: 10
       vni: 10100
       description: Tenant-A-Web
       vrf: Tenant-A
   ```
3. Run the manager:
   ```bash
   python examples/vxlan_fabric_manager.py --inventory fabric.yml --services services.yml
   ```
4. Supply credentials when prompted.  The script pushes configuration in
   parallel while streaming success/failure per node.

## Extending the automation

* Add new roles or device types by extending the `DeviceRole` enum and
  updating the configuration builder methods.
* Modify `build_feature_config`, `build_underlay_config`, and
  `build_overlay_config` to suit your standards.
* Add new service types by expanding `ServiceBundle` with additional data
  models and overriding the helper methods in `ServiceAwareConfigurator`.
* Use the YAML inventory file to separate environment data from code, making it
  easier to version-control your fabric topology.

Feel free to fork these scripts into your own automation framework or integrate
with task orchestrators such as Nornir, Salt, or Ansible.
