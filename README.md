# Python Automation Playbook for Data Center Network Engineers

This guide is designed as a practical, opinionated reference for Cisco Nexus (NX-OS) automation with Python. It assumes a network engineer's perspective and focuses on building maintainable, testable, and scalable tooling. The accompanying `examples/` directory contains runnable snippets that reinforce concepts from each section.

## 1. Python Fundamentals Refresher

### 1.1 Setting Up Your Environment
* Install Python 3.10+ and `pipx` for isolated CLIs.
* Use virtual environments (`python -m venv venv && source venv/bin/activate`) per project.
* Adopt a project layout like:
  ```text
  project/
  ├── README.md
  ├── pyproject.toml  # dependency management with Poetry/hatch/pip-tools
  ├── src/            # your Python packages
  ├── tests/          # pytest-based tests
  └── scripts/        # task entry points
  ```

### 1.2 Language Building Blocks
* **Primitive types:** `int`, `float`, `bool`, `str`, `None`.
* **Collections:** `list`, `tuple`, `set`, `dict`, `dataclass` (structured records).
* **Control flow:** `if/elif/else`, `for` loops (iterate over collections), `while` loops (repeat until condition changes), `match` (3.10+ pattern matching).
* **Error handling:** `try/except/else/finally`. Handle expected errors near where they occur; avoid broad `except Exception` unless you log/re-raise.
* **Modules & packages:** Organize reusable code into modules. Import only what you need to keep namespaces clear.

### 1.3 Essential Patterns
* Use **type hints** for all function arguments and return values to document intent and enable static analysis with `mypy`.
* Prefer **f-strings** for readability when formatting strings.
* **Context managers** (`with open(...)`) manage resources like files or network sessions cleanly.
* Handle sensitive data (passwords, tokens) via environment variables or secrets managers—never hard-code credentials.

See `examples/python_basics.py` for runnable demonstrations of data structures, loops, list/dict comprehensions, and context managers.

## 2. Structuring Code: Functions, Classes, and Modules

### 2.1 When to Write a Function
Functions are ideal for performing a single, well-defined task with input parameters and a return value.

* Use when logic can be described as "Given X, produce Y" (e.g., normalize interface names, parse API responses).
* Keep them short (≤20 lines is a good heuristic). Extract helper functions when you notice duplicate code or complex logic.
* Pure functions (no side effects) are easier to test. Prefer them for data transformations.

### 2.2 When to Create a Class
Classes encapsulate state and behavior that belong together.

* Use when you have a concept with lifecycle and data (e.g., an `NxosSwitch` that caches credentials, device facts, and provides methods like `get_vlans`).
* Classes help hide implementation details and expose a clean interface.
* Favor `dataclasses` for value objects (e.g., representing an interface or VLAN) with minimal boilerplate.
* Limit inheritance depth. Prefer **composition**—inject dependencies via the constructor rather than creating "God" classes.

`examples/functions_vs_classes.py` illustrates when to graduate from a procedural helper function to a class-based abstraction.

## 3. Looping Strategically

### 3.1 Choosing the Right Loop
* Use `for` loops to iterate over a known collection or generator.
* Use `while` loops when you must wait on a condition (e.g., polling a task until it completes).
* Prefer comprehensions (`[port.name for port in ports if port.is_up]`) for simple transformations; they are concise and expressive.
* Avoid deeply nested loops: extract inner loops into dedicated functions or generators.

### 3.2 Flattening Triple-Nested Loops
Example: iterating over data centers ➝ switches ➝ interfaces. Instead of three nested loops inline, create generators that yield work units and call reusable helper functions.

```python
from collections.abc import Iterable

def iter_work_items(datacenters: Iterable[dict]) -> Iterable[tuple[str, str, dict]]:
    for dc in datacenters:
        for switch in dc["switches"]:
            for interface in switch["interfaces"]:
                yield dc["name"], switch["hostname"], interface

for dc_name, hostname, interface in iter_work_items(dc_inventory):
    handle_interface(dc_name, hostname, interface)
```

By isolating the inner logic, you can test `iter_work_items` and `handle_interface` independently, and you can replace the generator with a version that fetches data asynchronously without modifying the calling loop.

### 3.3 Loop Control Best Practices
* Use `enumerate(sequence, start=1)` when you need index + value.
* Use `zip()` to iterate over multiple iterables in parallel.
* Break early with `break` or skip iterations with `continue` when it improves clarity.
* Guard complex loops with functions: `for interface in iter_switch_interfaces(inventory): ...`

See `examples/loop_strategies.py` for patterns that keep nested loops clean and testable.

## 4. Writing Modular, Scalable Automation

### 4.1 Project Layout
* **Core library (`src/`):** business logic, models, utilities.
* **Entry points (`scripts/`):** thin wrappers that parse CLI arguments and call core functions.
* **Configuration (`inventory/`, `settings.yaml`):** device definitions, credentials (encrypted), global defaults.
* **Tests (`tests/`):** unit tests (fast, isolated), integration tests (require lab or simulation).

### 4.2 Dependency Management
* Use `pyproject.toml` with Poetry or Hatch; lock dependencies for reproducible builds.
* Pin major versions of libraries like Nornir, NAPALM, and pyATS that you have tested.
* Use `.pre-commit-config.yaml` to run linters (e.g., `black`, `ruff`, `mypy`, `pytest`) before committing.

### 4.3 Configuration & Secrets
* Store inventory data in YAML/JSON, but keep secrets in encrypted vaults (Ansible Vault, SOPS, HashiCorp Vault).
* Use `.env` files with `python-dotenv` for local development (never commit them).
* Provide sane defaults and allow overrides via CLI flags or environment variables.

## 5. Concurrency & Scaling Workloads

### 5.1 Nornir Overview
[Nornir](https://nornir.readthedocs.io/) is a Python framework tailored for network automation. Key concepts:
* **Inventory:** hosts, groups, defaults.
* **Tasks:** Python callables executed per host.
* **Runner:** controls concurrency (threaded by default).

Example (`examples/nornir_threads.py`):
```python
from nornir import InitNornir
from nornir.core.task import Task, Result

def collect_facts(task: Task) -> Result:
    facts = task.run(task=napalm_get, getters=["facts"])
    hostname = facts.result["facts"]["hostname"]
    return Result(host=task.host, result=f"Got facts for {hostname}")

if __name__ == "__main__":
    nr = InitNornir(config_file="config.yaml")
    result = nr.run(task=collect_facts)
    result.print_results()
```
* Customize `nr = InitNornir(...)` with `num_workers` to control parallelism.
* Use `nr.filter()` to target device subsets.
* Combine Nornir with rich logging (structlog/loguru) to capture per-host activity.

### 5.2 Handling Massive Device Lists
* Partition devices by site or role and run tasks per batch.
* Use `nornir-salt` or job queues (Celery, Arq, Dramatiq) when tasks take minutes per host.
* Implement exponential backoff and retries for transient SSH/API failures.
* Use asynchronous libraries (`asyncio`, `asyncssh`, `scrapli`) when the tool supports it; Nornir 3+ offers experimental async runners.

### 5.3 Multitasking Without Nornir
* Use `concurrent.futures.ThreadPoolExecutor` for simple threaded workloads.
* For CPU-bound parsing (rare in network automation), use `ProcessPoolExecutor`.
* Rate-limit outbound connections with semaphores or token buckets to avoid overwhelming devices.

`examples/concurrency_threadpool.py` shows how to create a threaded worker pool with graceful shutdown.

## 6. Device Abstraction with NAPALM

[NAPALM](https://napalm.readthedocs.io/) provides a vendor-neutral API for reading and writing network state.

* Support for `get_facts`, `get_interfaces`, `load_merge_candidate`, `compare_config`, `commit_config`, and more.
* Works well inside Nornir via `nornir-napalm`. You can run compliance checks and configuration pushes while handling rollbacks automatically.
* Use `napalm_validate` to compare device state against a desired state expressed in YAML.

`examples/napalm_compliance.py` demonstrates loading a configuration candidate, diffing it, and committing or rolling back safely.

## 7. Testing with pyATS

[pyATS](https://developer.cisco.com/docs/pyats/) from Cisco is excellent for validation and CI pipelines.

* Define test cases with `aetest` classes.
* Use `Genie` parsers to normalize command outputs.
* Integrate pyATS with pytest by exporting pyATS testbeds and running them in GitLab/GitHub CI.

`examples/pyats_example.py` includes a small `aetest` suite that logs into NX-OS devices, gathers interface data via Genie, and validates policies.

## 8. Putting It Together: Workflow Blueprint

1. **Plan:** Define desired outcomes, success criteria, and rollback plans.
2. **Model:** Represent devices, interfaces, and policies as Python data structures (`dataclass`, `pydantic` models).
3. **Build:** Implement pure functions for parsing/transforming data and classes for device/session management.
4. **Automate:** Use Nornir or a custom runner to fan out tasks. Keep tasks idempotent.
5. **Observe:** Log every action, capture diffs, tag deployments with change IDs.
6. **Test:** Run unit tests, lint, and pyATS/Genie validations before and after changes.
7. **Release:** Use CI pipelines to package scripts, run tests, and deploy to automation servers.

## 9. Best Practices Checklist

* [ ] Every module has clear responsibilities and docstrings.
* [ ] Functions are single-purpose and annotated with types.
* [ ] Classes hide state transitions and expose intentional methods.
* [ ] Loops are shallow; reusable generators/functions flatten nested logic.
* [ ] Configuration and secrets are externalized and version-controlled securely.
* [ ] Concurrency is handled through frameworks (Nornir) or executors with robust error handling.
* [ ] Tests cover success, failure, and rollback paths; pyATS/Genie provides integration checks.
* [ ] Logging and metrics provide visibility into automation runs.
* [ ] CI enforces formatting (`black`), linting (`ruff`), typing (`mypy`), and testing (`pytest`, `pyats run job`).
* [ ] Documentation (like this README) stays up-to-date with tooling.

## 10. Further Learning

* Books: *Network Programmability and Automation (2nd Edition)*, *Automating and Orchestrating Networks with Ansible*.
* Cisco DevNet labs for pyATS/Genie and NX-OS automation.
* Community projects: `networktocode/nornir`, `ktbyers/netmiko`, `scrapli`.
* Practice in a sandbox (Cisco DevNet, EVE-NG, CML). Automate real workflows such as interface compliance, VLAN deployments, and configuration backups.

---

Explore the `examples/` directory to see how these principles translate into code. Clone this repository, create a virtual environment, install dependencies as needed, and adapt the snippets to your environment.
