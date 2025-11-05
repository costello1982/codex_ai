"""Loop patterns for scalable automation."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass(slots=True)
class Switch:
    name: str
    location: str
    interfaces: list[str]


@dataclass(slots=True)
class WorkItem:
    datacenter: str
    switch: str
    interface: str


def iter_interfaces(datacenters: Iterable[dict]) -> Iterator[WorkItem]:
    """Yield work items while flattening nested structures."""

    for datacenter in datacenters:
        for switch_data in datacenter["switches"]:
            switch = Switch(**switch_data)
            for interface in switch.interfaces:
                yield WorkItem(datacenter=datacenter["name"], switch=switch.name, interface=interface)


def batched(iterable: Iterable[WorkItem], batch_size: int) -> Iterator[list[WorkItem]]:
    """Group work items into batches to limit concurrent sessions."""

    batch: list[WorkItem] = []
    for item in iterable:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


if __name__ == "__main__":
    fabric_inventory = [
        {
            "name": "DC1",
            "switches": [
                {"name": "leaf-1", "location": "row-1", "interfaces": ["Eth1/1", "Eth1/2"]},
                {"name": "leaf-2", "location": "row-1", "interfaces": ["Eth1/1", "Eth1/48"]},
            ],
        },
        {
            "name": "DC2",
            "switches": [
                {"name": "leaf-5", "location": "row-3", "interfaces": ["Eth1/1"]},
            ],
        },
    ]

    for batch in batched(iter_interfaces(fabric_inventory), batch_size=2):
        print("Processing batch:")
        for item in batch:
            print(f"  {item.datacenter}/{item.switch} -> {item.interface}")
