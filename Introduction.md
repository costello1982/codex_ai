# Introduction to this FRR DC VXLAN EVPN Lab (Beginner Friendly)

This document explains the lab in simple terms and focuses on:

- what VXLAN EVPN is,
- how traffic moves in this topology,
- who is the gateway for clients,
- why default routes exist in both VRFs,
- and exactly how to troubleshoot routing/VRFs/learned paths.

---

## 1) What this lab is trying to teach

This project simulates a **small data-center fabric** using FRR routers in containerlab:

- 2 Spines
- 3 Leaves
- 1 Edge router (simulated “internet” by advertising `8.8.8.8/32`)
- 1 Firewall (FRR + iptables)
- 2 Clients

You can test:

1. Underlay routing (spine-leaf reachability)
2. EVPN control plane between leaves and spines
3. Per-VRF service routing (Blue and Red)
4. Firewall policy/NAT as north-south gateway
5. Internet path simulation to `8.8.8.8`

---

## 2) Quick VXLAN EVPN explanation (simple)

Think of it as two layers:

### Underlay (transport network)
- This is the IP network between spines and leaves.
- In this lab, underlay uses eBGP between spines and leaves.
- Its job: make sure all fabric nodes can reach each other.

### Overlay (service/network virtualization)
- This is where tenant/service networks are represented (Blue/Red VRFs + VNIs).
- EVPN (using BGP) distributes route information for those VRFs.
- Its job: make separate logical networks behave consistently across leaves.

In short:
- **Underlay carries packets between routers**.
- **Overlay decides which tenant/service route belongs where**.

---

## 3) Who is the gateway for clients?

In this design, the **firewall (`fw1`) is the service gateway** toward external networks.

- Client1 belongs to Blue side.
- Client2 belongs to Red side.
- Leaf routers provide the first routed hop from client links.
- Firewall is connected with dedicated L3 transit links per VRF:
  - Blue transit: `leaf1 <-> fw1` (`172.16.10.0/31`)
  - Red transit: `leaf1 <-> fw1` (`172.16.20.0/31`)
- Firewall also has an outside link toward leaf1 (`172.31.0.4/31` side on leaf1, `172.31.0.5/31` on fw1), then leaf1 reaches edge1 (`172.31.0.0/31`) where `8.8.8.8/32` is advertised.

So operationally:
- **Default route for Blue/Red services is learned from firewall** (BGP default-originate on fw1 per VRF).
- Firewall then forwards/NATs traffic toward outside.

---

## 4) “How do clients know to go to firewall for other subnets?”

Great question. Routers and hosts do this based on routing tables:

1. A client compares destination IP with its directly connected subnet.
2. If destination is not local, it uses its default route.
3. Its upstream leaf receives traffic and looks up route in the relevant VRF.
4. If destination is external/unknown tenant subnet, leaf uses **default route learned from firewall**.
5. Firewall applies policy/NAT and forwards toward outside network.

So clients do not “know firewall directly” in all cases; they know **their next-hop/gateway path**. The leaf and VRF routing logic then steers traffic to firewall for non-local destinations.

---

## 5) Why is default route advertised in both VRFs?

Because Blue and Red are separate routing domains.

- `router bgp ... vrf blue` has `default-originate` toward leaf
- `router bgp ... vrf red` has `default-originate` toward leaf

This means each VRF gets its own `0.0.0.0/0`, allowing both service domains to reach external destinations via firewall.

Without this, one (or both) VRFs might have no path to internet or external prefixes.

---

## 6) How to troubleshoot step-by-step

## A. Check lab/container state

```bash
containerlab inspect -t frr-dc-vxlan-evpn/topology/clab-frr-dc-vxlan-evpn.yml
```

Verify all nodes are in `running` state.

---

## B. Check VRFs on a node

### Linux VRF view (kernel side)

```bash
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 ip -d link show type vrf
docker exec -it clab-frr-dc-vxlan-evpn-fw1 ip -d link show type vrf
```

### FRR view (routing side)

```bash
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show vrf'
docker exec -it clab-frr-dc-vxlan-evpn-fw1 vtysh -c 'show vrf'
```

---

## C. Check BGP sessions

### Underlay BGP

```bash
docker exec -it clab-frr-dc-vxlan-evpn-spine1 vtysh -c 'show bgp summary'
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp summary'
```

### EVPN control plane

```bash
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp l2vpn evpn summary'
```

### Per-VRF BGP neighbors/routes

```bash
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp vrf blue ipv4 summary'
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp vrf red ipv4 summary'
docker exec -it clab-frr-dc-vxlan-evpn-fw1 vtysh -c 'show bgp vrf blue ipv4 summary'
docker exec -it clab-frr-dc-vxlan-evpn-fw1 vtysh -c 'show bgp vrf red ipv4 summary'
```

---

## D. See routes inside each VRF

### Kernel/FIB routes per VRF

```bash
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 ip route show vrf blue
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 ip route show vrf red
docker exec -it clab-frr-dc-vxlan-evpn-fw1 ip route show vrf blue
docker exec -it clab-frr-dc-vxlan-evpn-fw1 ip route show vrf red
```

### FRR RIB routes per VRF

```bash
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show ip route vrf blue'
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show ip route vrf red'
```

---

## E. “From where did this IP route get learned?”

Use these commands:

```bash
# Specific prefix in VRF Blue
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp vrf blue ipv4 0.0.0.0/0'

# Specific host route example
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp vrf blue ipv4 8.8.8.8/32'

# Full table with next-hops and path attributes
docker exec -it clab-frr-dc-vxlan-evpn-leaf1 vtysh -c 'show bgp vrf blue ipv4'
```

What to look for:
- **Next hop** (who sent it / where traffic goes)
- **Path attributes** (AS path, local-pref, MED)
- **Best path marker (`*>`)**
- **Installed in FIB** indicator

If a route is in BGP but not in kernel route table, check policy/filtering/next-hop reachability.

---

## F. Validate data-plane with ping/traceroute

```bash
docker exec -it clab-frr-dc-vxlan-evpn-client1 ping -c 3 172.16.10.1
docker exec -it clab-frr-dc-vxlan-evpn-client2 ping -c 3 172.16.20.1
docker exec -it clab-frr-dc-vxlan-evpn-client1 ping -c 3 8.8.8.8
docker exec -it clab-frr-dc-vxlan-evpn-client2 ping -c 3 8.8.8.8

docker exec -it clab-frr-dc-vxlan-evpn-client1 traceroute 8.8.8.8
docker exec -it clab-frr-dc-vxlan-evpn-client2 traceroute 8.8.8.8
```

---

## G. Check firewall rules and counters

```bash
docker exec -it clab-frr-dc-vxlan-evpn-fw1 iptables -S
docker exec -it clab-frr-dc-vxlan-evpn-fw1 iptables -t nat -S
docker exec -it clab-frr-dc-vxlan-evpn-fw1 iptables -L -n -v
```

Counters increasing on expected rules confirm real forwarding/NAT path.

---

## 7) Common issues and what they usually mean

- **BGP neighbor stuck in Active/Connect**
  - Interface IP mismatch, wrong AS, link down, or daemon not up.

- **Route present in BGP but traffic still fails**
  - Missing kernel route install, policy/iptables block, missing return path.

- **Can ping firewall transit but not 8.8.8.8**
  - Check default route propagation, edge route advertisement, NAT rules.

- **One VRF works, other fails**
  - Usually per-VRF BGP neighbor/default-originate mismatch.

---

## 8) How to safely extend this lab

1. Add/modify firewall policy in:
   - `frr-dc-vxlan-evpn/firewall/iptables.rules.v4`
2. Re-apply quickly:
   ```bash
   docker exec -i clab-frr-dc-vxlan-evpn-fw1 iptables-restore < frr-dc-vxlan-evpn/firewall/iptables.rules.v4
   ```
3. Add more clients by:
   - creating new link(s) in topology,
   - adding FRR config with per-VRF BGP or static routes,
   - validating with `show ip route vrf <name>` and ping/traceroute.

---

## 9) Mental model (easy memory)

- **Leafs = fabric access + tenant routing context**
- **Spines = transport core + EVPN control reflection**
- **Firewall = policy/NAT internet gateway for Blue/Red VRFs**
- **Edge = fake internet endpoint (`8.8.8.8`)**

If you remember this flow, troubleshooting becomes much easier.
