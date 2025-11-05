"""Example Nornir task for collecting NX-OS facts in parallel."""

from __future__ import annotations

from nornir import InitNornir
from nornir.core.filter import F
from nornir.core.task import Result, Task
from nornir_napalm.plugins.tasks import napalm_get


def collect_switch_facts(task: Task) -> Result:
    """Fetch basic facts from a switch via NAPALM."""

    response = task.run(task=napalm_get, getters=["facts", "interfaces"])
    facts = response.result["facts"]
    hostname = facts["hostname"]
    serial = facts.get("serial_number", "unknown")
    return Result(host=task.host, result={"hostname": hostname, "serial": serial})


if __name__ == "__main__":
    nr = InitNornir(config_file="config.yaml")

    # Filter to only Nexus switches in the production group.
    nexus = nr.filter(F(platform="nxos"), F(groups__contains="production"))

    result = nexus.run(task=collect_switch_facts)
    for host, host_result in result.items():
        facts = host_result[0].result  # The first entry is the return value from collect_switch_facts
        print(f"{host}: hostname={facts['hostname']} serial={facts['serial']}")
