# FRR DC VXLAN EVPN (containerlab)

> New to EVPN? Start with `Introduction.md` for a beginner walkthrough.

This repository contains a ready-to-use **containerlab** project for a small data-center fabric built with **FRR**:

- 2x Spine routers (FRR)
- 3x Leaf routers (FRR)
- 1x Edge router (FRR) simulating internet reachability to `8.8.8.8`
- 1x Firewall node (FRR + iptables)
- 2x L3 clients in different service domains (Blue/Red)
- Client1 is dual-homed to two different leaves for ECMP-style upstream redundancy

## Topology Overview

Project path:

- `frr-dc-vxlan-evpn/topology/clab-frr-dc-vxlan-evpn.yml`

High-level design:

1. **Underlay:** eBGP between Spines and Leaves
2. **Overlay:** EVPN control-plane signaling from Leaves through Spine route-reflectors
3. **Service Segments:** Blue and Red VRF-oriented routing model on Leaves/Firewall
4. **Internet Simulation:** `edge1` advertises `8.8.8.8/32`
5. **Firewall:** policy control and NAT via `iptables.rules.v4`

## Directory Layout

```text
frr-dc-vxlan-evpn/
├── topology/
│   └── clab-frr-dc-vxlan-evpn.yml
├── configs/
│   ├── spine1/frr.conf
│   ├── spine2/frr.conf
│   ├── leaf1/frr.conf
│   ├── leaf2/frr.conf
│   ├── leaf3/frr.conf
│   ├── edge1/frr.conf
│   ├── fw1/frr.conf
│   ├── client1/frr.conf
│   └── client2/frr.conf
├── firewall/
│   └── iptables.rules.v4
└── scripts/
    ├── setup-leaf-vrfs.sh
    └── setup-firewall.sh
```

## Addressing and Roles

- Underlay links: `10.0.0.0/31` blocks between spines and leaves
- Loopbacks:
  - Spines: `10.255.0.1/32`, `10.255.0.2/32`
  - Leaves: `10.255.1.1/32` .. `10.255.1.3/32`
- Internet simulator on edge: loopback `8.8.8.8/32`
- Firewall transit links:
  - Blue VRF transit: `172.16.10.0/31`
  - Red VRF transit: `172.16.20.0/31`
  - Outside transit: `172.31.0.4/31`
- Client links:
  - Client1 dual-homed (Leaf1 + Leaf2): `10.10.10.0/31`, `10.10.10.2/31`
  - Client2 single-homed (Leaf3): `10.20.20.0/31`

## Firewall Rules (Easy to Extend)

The firewall policy is stored in:

- `frr-dc-vxlan-evpn/firewall/iptables.rules.v4`

Current behavior:

- Allows established/related flows
- Allows Blue and Red segments to go out via outside interface
- Allows Blue ↔ Red forwarding (for lab validation)
- NATs client source ranges to outside interface

To extend policy later, edit this file and re-apply:

```bash
docker exec -it clab-frr-dc-vxlan-evpn-fw1 iptables-restore < frr-dc-vxlan-evpn/firewall/iptables.rules.v4
```

## Deploy

From repository root:

```bash
containerlab deploy -t frr-dc-vxlan-evpn/topology/clab-frr-dc-vxlan-evpn.yml
```

Destroy lab:

```bash
containerlab destroy -t frr-dc-vxlan-evpn/topology/clab-frr-dc-vxlan-evpn.yml
```

## Basic Validation Workflow

1. Verify BGP sessions on spines/leaves
2. Verify EVPN routes on leaves
3. Verify client routes are present in service VRFs
4. Verify firewall learned paths and default-originate behavior
5. Verify reachability from clients to firewall and to `8.8.8.8`

## Troubleshooting Commands

### containerlab

```bash
containerlab inspect -t frr-dc-vxlan-evpn/topology/clab-frr-dc-vxlan-evpn.yml
containerlab graph -t frr-dc-vxlan-evpn/topology/clab-frr-dc-vxlan-evpn.yml
```

### FRR checks

```bash
docker exec -it clab-frr-dc-vxlan-evpn-spine1 vtysh -c 'show bgp summary'
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp summary'
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp l2vpn evpn summary'
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp vrf blue ipv4 summary'
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp vrf red ipv4 summary'
docker exec -it clab-frr-dc-vxlan-evpn-fw1 vtysh -c 'show bgp vrf blue ipv4 summary'
docker exec -it clab-frr-dc-vxlan-evpn-fw1 vtysh -c 'show bgp vrf red ipv4 summary'
```

### Firewall policy + NAT checks

```bash
docker exec -it clab-frr-dc-vxlan-evpn-fw1 iptables -S
docker exec -it clab-frr-dc-vxlan-evpn-fw1 iptables -t nat -S
docker exec -it clab-frr-dc-vxlan-evpn-fw1 iptables -L -n -v
```

### Connectivity checks

```bash
docker exec -it clab-frr-dc-vxlan-evpn-client1 ping -c 3 172.16.10.1
docker exec -it clab-frr-dc-vxlan-evpn-client2 ping -c 3 172.16.20.1
docker exec -it clab-frr-dc-vxlan-evpn-client1 ping -c 3 8.8.8.8
docker exec -it clab-frr-dc-vxlan-evpn-client2 ping -c 3 8.8.8.8
```

### Path debugging

```bash
docker exec -it clab-frr-dc-vxlan-evpn-client1 traceroute 8.8.8.8
docker exec -it clab-frr-dc-vxlan-evpn-client2 traceroute 8.8.8.8
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 ip route
```
