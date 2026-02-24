#!/usr/bin/env bash
set -euo pipefail

ip link add vrf-blue type vrf table 1001 || true
ip link add vrf-red type vrf table 1002 || true
ip link set vrf-blue up
ip link set vrf-red up
ip link set eth1 master vrf-blue || true
ip link set eth2 master vrf-red || true

sysctl -w net.ipv4.ip_forward=1 >/dev/null

iptables-restore < /workspace/firewall/iptables.rules.v4

echo "[fw1] firewall + vrfs initialized"
