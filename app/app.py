import ipaddress
import math
from typing import Any, Dict, List, Optional, Tuple

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


def _parse_vlsm_requirements(requirements_input: str) -> List[Tuple[str, int]]:
    requirements: List[Tuple[str, int]] = []
    for index, line in enumerate(requirements_input.splitlines(), start=1):
        cleaned = line.strip()
        if not cleaned:
            continue

        if ":" in cleaned:
            name_part, host_part = cleaned.split(":", 1)
        elif "," in cleaned:
            name_part, host_part = cleaned.split(",", 1)
        else:
            name_part, host_part = f"Subnet {index}", cleaned

        name = name_part.strip() or f"Subnet {index}"

        try:
            hosts = int(host_part.strip())
        except ValueError as exc:
            raise ValueError(f"Could not parse host requirement on line {index}: '{cleaned}'") from exc

        if hosts <= 0:
            raise ValueError(f"Host requirement must be positive on line {index}: '{cleaned}'")

        requirements.append((name, hosts))

    if not requirements:
        raise ValueError("Provide at least one department/host pair for VLSM calculation.")

    return requirements


def _hosts_to_prefix(hosts: int) -> Tuple[int, int]:
    if hosts <= 0:
        raise ValueError("Host requirement must be positive.")

    if hosts == 1:
        return 32, 1

    if hosts == 2:
        return 31, 2

    required_addresses = hosts + 2
    exponent = math.ceil(math.log2(required_addresses))
    prefix = 32 - exponent
    total_addresses = 2 ** exponent

    if prefix < 0:
        raise ValueError("Host requirement exceeds IPv4 address capacity.")

    return prefix, total_addresses


def calculate_vlsm(base_network_input: str, requirements_input: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        base_network = ipaddress.IPv4Network(base_network_input, strict=False)
    except ValueError as exc:
        return None, f"Invalid base network: {exc}"

    try:
        requirements = _parse_vlsm_requirements(requirements_input)
    except ValueError as exc:
        return None, str(exc)

    allocations: List[Dict[str, Any]] = []
    current_int = int(base_network.network_address)
    base_end = int(base_network.broadcast_address)

    # Sort requirements by descending host need to satisfy largest subnets first.
    requirements_sorted = sorted(requirements, key=lambda item: item[1], reverse=True)

    for name, hosts in requirements_sorted:
        try:
            prefix, block_size = _hosts_to_prefix(hosts)
        except ValueError as exc:
            return None, str(exc)

        remainder = current_int % block_size
        if remainder != 0:
            current_int += block_size - remainder

        if current_int > base_end:
            return None, f"Not enough address space remaining for {name}."

        if current_int + block_size - 1 > base_end:
            return None, f"{name} does not fit inside {base_network.with_prefixlen}."

        subnet = ipaddress.IPv4Network((ipaddress.IPv4Address(current_int), prefix))

        if not subnet.subnet_of(base_network):
            return None, f"{subnet.with_prefixlen} is outside of {base_network.with_prefixlen}."

        total_hosts = subnet.num_addresses
        if subnet.prefixlen >= 31:
            usable_hosts = total_hosts
            hosts_range = list(subnet.hosts())
            if usable_hosts == 1:
                first_host = last_host = str(hosts_range[0])
            else:
                first_host, last_host = str(hosts_range[0]), str(hosts_range[-1])
        else:
            usable_hosts = total_hosts - 2
            first_host = str(subnet.network_address + 1)
            last_host = str(subnet.broadcast_address - 1)

        allocations.append(
            {
                "name": name,
                "requested_hosts": hosts,
                "network": subnet.with_prefixlen,
                "netmask": str(subnet.netmask),
                "prefix": subnet.prefixlen,
                "total_addresses": total_hosts,
                "usable_hosts": usable_hosts,
                "first_host": first_host,
                "last_host": last_host,
            }
        )

        current_int += block_size

    remaining_networks: List[str] = []
    if current_int <= base_end:
        leftover_start = ipaddress.IPv4Address(current_int)
        leftover_networks = ipaddress.summarize_address_range(leftover_start, base_network.broadcast_address)
        remaining_networks = [net.with_prefixlen for net in leftover_networks]

    allocated_addresses = sum(item["total_addresses"] for item in allocations)
    remaining_addresses = base_network.num_addresses - allocated_addresses

    result: Dict[str, Any] = {
        "base_network": base_network.with_prefixlen,
        "total_addresses": base_network.num_addresses,
        "allocations": allocations,
        "remaining_networks": remaining_networks,
        "requested_hosts": sum(hosts for _, hosts in requirements),
        "allocated_addresses": allocated_addresses,
        "remaining_addresses": remaining_addresses,
    }

    return result, None


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    ipv4_result: Optional[Dict[str, Any]] = None
    ipv4_error: Optional[str] = None
    ipv6_result: Optional[Dict[str, Any]] = None
    ipv6_error: Optional[str] = None
    vlsm_result: Optional[Dict[str, Any]] = None
    vlsm_error: Optional[str] = None

    if request.method == "POST":
        form_type = request.form.get("form_type", "")

        if form_type == "ipv4":
            ipv4_input = request.form.get("ipv4_network", "").strip()
            if ipv4_input:
                ipv4_result, ipv4_error = calculate_ipv4(ipv4_input)
            else:
                ipv4_error = "Please enter an IPv4 network in CIDR notation."
        elif form_type == "ipv6":
            ipv6_input = request.form.get("ipv6_network", "").strip()
            if ipv6_input:
                ipv6_result, ipv6_error = calculate_ipv6(ipv6_input)
            else:
                ipv6_error = "Please enter an IPv6 network in CIDR notation."
        elif form_type == "vlsm":
            base_network = request.form.get("vlsm_base_network", "").strip()
            requirements = request.form.get("vlsm_requirements", "").strip()
            if not base_network:
                vlsm_error = "Please provide an IPv4 network to subdivide."
            elif not requirements:
                vlsm_error = "Please list at least one department and host requirement."
            else:
                vlsm_result, vlsm_error = calculate_vlsm(base_network, requirements)

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
        vlsm_result=vlsm_result,
        vlsm_error=vlsm_error,
        cheat_sheet=cheat_sheet,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
