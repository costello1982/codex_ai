"""NAPALM compliance workflow example."""

from __future__ import annotations

from pathlib import Path

from napalm import get_network_driver


def load_candidate_config(hostname: str, username: str, password: str, candidate_path: Path) -> None:
    """Connect to a device, load a config candidate, diff, and commit."""

    driver = get_network_driver("nxos")
    with driver(hostname, username, password) as device:
        device.open()
        device.load_merge_candidate(filename=str(candidate_path))
        diff = device.compare_config()
        if diff:
            print(f"Diff for {hostname}:\n{diff}")
            confirmation = input("Apply changes? [y/N]: ").strip().lower()
            if confirmation == "y":
                device.commit_config()
                print("Committed")
            else:
                device.discard_config()
                print("Discarded")
        else:
            print(f"No changes required on {hostname}")


if __name__ == "__main__":
    load_candidate_config(
        hostname="leaf-1.example.com",
        username="automation",
        password="super-secret",
        candidate_path=Path("configs/leaf-1_merge.txt"),
    )
