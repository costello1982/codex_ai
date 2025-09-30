import ipaddress
from typing import Any, Dict, Optional, Tuple

from flask import Flask, render_template, request

app = Flask(__name__)


def calculate_ipv4(network_input: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        network = ipaddress.IPv4Network(network_input, strict=False)
    except ValueError as exc:
        return None, str(exc)

    total_hosts = network.num_addresses
    usable_hosts = max(total_hosts - 2, 0) if network.prefixlen < 31 else total_hosts

    if total_hosts == 0:
        first_host = last_host = "N/A"
    elif total_hosts == 1:
        first_host = last_host = str(network.network_address)
    elif network.prefixlen == 31:
        hosts = list(network.hosts())
        first_host, last_host = str(hosts[0]), str(hosts[-1])
    else:
        first_host = str(network.network_address + 1)
        last_host = str(network.broadcast_address - 1)

    info: Dict[str, Any] = {
        "version": "IPv4",
        "network": str(network.network_address),
        "netmask": str(network.netmask),
        "hostmask": str(network.hostmask),
        "broadcast": str(network.broadcast_address),
        "prefix": network.prefixlen,
        "total_hosts": total_hosts,
        "usable_hosts": usable_hosts,
        "first_host": first_host,
        "last_host": last_host,
        "private": network.is_private,
        "multicast": network.is_multicast,
        "loopback": network.is_loopback,
    }
    return info, None


def calculate_ipv6(network_input: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        network = ipaddress.IPv6Network(network_input, strict=False)
    except ValueError as exc:
        return None, str(exc)

    info: Dict[str, Any] = {
        "version": "IPv6",
        "network": str(network.network_address),
        "compressed": network.compressed,
        "exploded": network.exploded,
        "prefix": network.prefixlen,
        "max_prefix_len": network.max_prefixlen,
        "total_hosts": network.num_addresses,
        "private": network.is_private,
        "multicast": network.is_multicast,
        "loopback": network.is_loopback,
        "global": network.is_global,
    }
    return info, None


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    ipv4_result: Optional[Dict[str, Any]] = None
    ipv4_error: Optional[str] = None
    ipv6_result: Optional[Dict[str, Any]] = None
    ipv6_error: Optional[str] = None

    if request.method == "POST":
        ipv4_input = request.form.get("ipv4_network", "").strip()
        ipv6_input = request.form.get("ipv6_network", "").strip()

        if ipv4_input:
            ipv4_result, ipv4_error = calculate_ipv4(ipv4_input)
        if ipv6_input:
            ipv6_result, ipv6_error = calculate_ipv6(ipv6_input)

    cheat_sheet = {
        "IPv4": [
            "32-bit addresses, typically written as dotted decimal (e.g., 192.168.1.0)",
            "Default subnet masks: /8 (255.0.0.0), /16 (255.255.0.0), /24 (255.255.255.0)",
            "Private ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16",
            "Loopback range: 127.0.0.0/8",
            "Link-local range: 169.254.0.0/16",
        ],
        "IPv6": [
            "128-bit addresses represented in hexadecimal (e.g., 2001:0db8::/32)",
            "Interface ID is typically 64 bits (e.g., /64 networks)",
            "Loopback address: ::1",
            "Link-local range: fe80::/10",
            "Unique local addresses (private): fc00::/7",
        ],
        "Subnetting": [
            "CIDR notation expresses prefix length (e.g., /24)",
            "Smaller prefix = more hosts, larger prefix = fewer hosts",
            "/30 and /31 IPv4 networks are common for point-to-point links",
            "Use ipcalc-like utilities to verify network allocations",
        ],
        "Public vs Private": [
            "Private addresses are not routed on the public internet",
            "Public addresses must be globally unique",
            "Multicast ranges: IPv4 224.0.0.0/4, IPv6 ff00::/8",
        ],
    }

    return render_template(
        "index.html",
        ipv4_result=ipv4_result,
        ipv4_error=ipv4_error,
        ipv6_result=ipv6_result,
        ipv6_error=ipv6_error,
        cheat_sheet=cheat_sheet,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
