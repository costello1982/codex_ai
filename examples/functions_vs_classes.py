"""Deciding between functions and classes.

This file demonstrates when simple helper functions are enough and when a
class provides a cleaner abstraction with lifecycle management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from python_basics import Interface


def build_interface_map(interfaces: Iterable[Interface]) -> dict[str, Interface]:
    """Return a name ➝ Interface mapping using a pure function."""

    return {interface.name: interface for interface in interfaces}


@dataclass(slots=True)
class ChangeTicket:
    """Encapsulate the state and workflow for an automation change ticket."""

    change_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    devices: list[str] = field(default_factory=list)
    completed: bool = False

    def add_device(self, hostname: str) -> None:
        if hostname not in self.devices:
            self.devices.append(hostname)

    def mark_complete(self) -> None:
        self.completed = True

    def to_payload(self) -> dict[str, str | bool | list[str]]:
        """Return a serializable representation for APIs or logs."""

        return {
            "change_id": self.change_id,
            "created_at": self.created_at.isoformat(),
            "devices": self.devices,
            "completed": self.completed,
        }


if __name__ == "__main__":
    demo_interfaces = [
        Interface(name="Eth1/1", enabled=True),
        Interface(name="Eth1/48", enabled=False),
    ]
    interface_map = build_interface_map(demo_interfaces)
    print("Interface map:", interface_map)

    ticket = ChangeTicket(change_id="CHG12345")
    for hostname in ["leaf-1", "leaf-2"]:
        ticket.add_device(hostname)
    ticket.mark_complete()
    print("Ticket payload:", ticket.to_payload())
