"""Foundational Python patterns for network engineers.

This module demonstrates:
* Working with built-in data structures.
* Iterating with loops and comprehensions.
* Building reusable functions with type hints.
* Using context managers to handle files safely.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Interface:
    """Simple representation of a network interface."""

    name: str
    enabled: bool
    description: str | None = None


def up_interface_names(interfaces: Iterable[Interface]) -> list[str]:
    """Return the names of all enabled interfaces."""

    return [iface.name for iface in interfaces if iface.enabled]


def normalize_description(description: str | None) -> str:
    """Return a cleaned description string suitable for configuration templates."""

    if not description:
        return "UNCONFIGURED"
    return description.strip().upper()


def summarize_interfaces(interfaces: Iterable[Interface]) -> dict[str, Any]:
    """Summarize interface state for reporting or templating."""

    interfaces = list(interfaces)
    return {
        "total": len(interfaces),
        "enabled": len([iface for iface in interfaces if iface.enabled]),
        "disabled": len([iface for iface in interfaces if not iface.enabled]),
        "names": [iface.name for iface in interfaces],
    }


def save_report(path: str, summary: dict[str, Any]) -> None:
    """Persist a JSON-like summary to disk using a context manager."""

    lines = [f"{key}: {value}\n" for key, value in summary.items()]
    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)


if __name__ == "__main__":
    inventory = [
        Interface(name="Eth1/1", enabled=True, description="Uplink to DC1"),
        Interface(name="Eth1/2", enabled=False, description=None),
        Interface(name="Eth1/3", enabled=True, description=" server-101 "),
    ]

    print("Enabled interfaces:", up_interface_names(inventory))
    print("Normalized descriptions:", [normalize_description(i.description) for i in inventory])
    summary = summarize_interfaces(inventory)
    print("Summary:", summary)
    save_report("interface_report.txt", summary)
    print("Report written to interface_report.txt")
