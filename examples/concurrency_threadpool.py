"""ThreadPoolExecutor pattern for running tasks across many switches."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def collect_facts(hostname: str) -> str:
    """Placeholder for a function that connects to a device and gathers data."""

    # Replace this with real logic (e.g., NAPALM, Scrapli, custom API calls).
    LOGGER.info("Collecting facts for %s", hostname)
    return f"Facts for {hostname}"


def run_in_threads(hosts: Iterable[str], max_workers: int = 20) -> dict[str, str]:
    """Execute `collect_facts` concurrently while handling failures gracefully."""

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(collect_facts, host): host for host in hosts}
        for future in as_completed(future_map):
            host = future_map[future]
            try:
                results[host] = future.result()
            except Exception as exc:  # noqa: BLE001 - log and continue
                LOGGER.exception("%s failed: %s", host, exc)
    return results


if __name__ == "__main__":
    device_list = [f"leaf-{index}" for index in range(1, 11)]
    aggregated = run_in_threads(device_list, max_workers=4)
    print(aggregated)
