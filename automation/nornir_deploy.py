#!/usr/bin/env python3
"""Deploy rendered configs to NX-OS fabric using Nornir + scrapli."""

from __future__ import annotations

from pathlib import Path

from nornir import InitNornir
from nornir.core.task import Task, Result
from nornir_scrapli.tasks import send_config, send_command

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "generated"


def push_device_config(task: Task) -> Result:
    cfg_file = GENERATED_DIR / f"{task.host.name}.cfg"
    if not cfg_file.exists():
        return Result(
            host=task.host,
            failed=True,
            changed=False,
            result=f"Missing generated config for {task.host.name}: {cfg_file}",
        )

    config_lines = [line for line in cfg_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    task.run(task=send_config, configs=config_lines)
    check = task.run(task=send_command, command="show bgp l2vpn evpn summary", name="post_check")
    return Result(host=task.host, changed=True, result=check.result)


def main() -> None:
    nr = InitNornir(
        runner={"plugin": "threaded", "options": {"num_workers": 10}},
        inventory={
            "plugin": "SimpleInventory",
            "options": {
                "host_file": str(ROOT / "inventory" / "hosts.yaml"),
                "group_file": str(ROOT / "inventory" / "groups.yaml"),
                "defaults_file": str(ROOT / "inventory" / "defaults.yaml"),
            },
        },
    )

    results = nr.run(task=push_device_config)
    for host, output in results.items():
        state = "FAILED" if output.failed else "OK"
        print(f"{host}: {state}")


if __name__ == "__main__":
    main()
