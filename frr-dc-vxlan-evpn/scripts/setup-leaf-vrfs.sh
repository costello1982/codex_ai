#!/usr/bin/env bash
set -euo pipefail

NODE_NAME="${1:-leaf}"

ip link add vrf-blue type vrf table 1001 || true
ip link add vrf-red type vrf table 1002 || true
ip link set vrf-blue up
ip link set vrf-red up

# Attach service-facing interfaces when present
for intf in eth4 eth7; do
  ip link set "$intf" master vrf-blue 2>/dev/null || true
done
for intf in eth5; do
  ip link set "$intf" master vrf-red 2>/dev/null || true
done

# ECMP test client links on leaf2/leaf3 should stay in default VRF unless explicitly set above.
sysctl -w net.ipv4.ip_forward=1 >/dev/null

echo "[$NODE_NAME] VRFs ready"
