# Python & Network Automation Quick Reference

This quick-reference is designed as your companion when learning Python with a focus on data-center network automation (NX-OS, Nornir, NAPALM, pyATS, etc.). It supplements the main `README.md` playbook by providing concise definitions, when-to-use guidance, and discovery tips.

## Core Python Building Blocks

### Numbers: `int` and `float`
- **`int`** (integer) represents whole numbers, e.g., VLAN IDs or interface counts.
  ```python
  vlan_id = 200  # good for VLANs, ASN, counts
  ```
  *Use when exact whole numbers are needed.*
- **`float`** represents decimal numbers, e.g., link utilization percentages.
  ```python
  cpu_utilization = 67.5  # percentage with decimals
  ```
  *Use when measurements can contain fractions.*

### `bool`
- Stores `True` or `False` (binary decisions, feature toggles).
  ```python
  is_nexus = True
  maintenance_mode = False
  ```
  *Use for status flags or conditional checks.*

### `str`
- Text data: hostnames, IPs, CLI commands.
  ```python
  hostname = "leaf01"
  interface = "Ethernet1/1"
  ```
  *Use when storing textual identifiers or command strings.*

### Collections
- **`list`**: ordered, mutable sequence. Great for queues of tasks or device lists.
  ```python
  devices = ["leaf01", "leaf02", "spine01"]
  devices.append("spine02")
  ```
  *Use when order matters and items may change.*
- **`tuple`**: ordered, immutable sequence. Useful for fixed groupings like (ip, port).
  ```python
  netconf_endpoint = ("10.10.10.5", 830)
  ```
  *Use for read-only pairs or coordinate-style data.*
- **`dict`**: key-value mapping. Ideal for structured device facts.
  ```python
  device = {
      "hostname": "leaf01",
      "mgmt_ip": "10.1.1.10",
      "role": "leaf",
      "vlans": [10, 20, 30]
  }
  ```
  *Use when you want fast lookups by a key.*
- **`set`** (bonus): unordered unique items. Handy for deduplicating VLANs or IPs.
  ```python
  vlans_seen = {10, 20, 20, 30}  # becomes {10, 20, 30}
  ```

### Control Flow: `if`, `elif`, `else`
- Choose actions based on conditions (device role, feature state).
  ```python
  if device["role"] == "spine":
      template = "spine_template.j2"
  elif device["role"] == "leaf":
      template = "leaf_template.j2"
  else:
      template = "default_template.j2"
  ```
  *Use to branch logic depending on device attributes or test results.*

### Looping Constructs
- **`for` loops** iterate over known collections (devices, interfaces, VLAN IDs).
  ```python
  for device in devices:
      deploy_vlan(device, vlan_id=200)
  ```
- **Nested `for` loops** are acceptable when the relationships are natural (device → interface → command).
  ```python
  for device in devices:
      for iface in device_interfaces(device):
          for command in interface_commands(iface):
              push_command(device, command)
  ```
  *Keep each loop focused. Extract helper functions to avoid deeply indented code.*
- **`while` loops** repeat until a condition changes (polling job progress, waiting for convergence).
  ```python
  while not change_request.done():
      time.sleep(5)
      change_request.refresh()
  ```
  *Use when you cannot precompute how many iterations are needed.*

### Functions vs. Classes
- **Functions**: encapsulate a single task or calculation.
  ```python
  def get_spine_devices(inventory):
      return [d for d in inventory if d["role"] == "spine"]
  ```
  *Use for stateless utilities or one-off actions.*
- **Classes**: bundle state + behavior (e.g., connection sessions, reusable clients).
  ```python
  class VlanDeployer:
      def __init__(self, nornir):
          self.nornir = nornir

      def deploy(self, vlan_id):
          self.nornir.run(task=configure_vlan, vlan_id=vlan_id)
  ```
  *Use when you need to maintain context across multiple operations.*

## Discovering Python Features Quickly

- **Built-in help**:
  ```python
  help(str)
  dir(device)
  ```
- **Official docs**: https://docs.python.org/3/ (search bar + library reference).
- **Search tips**: use `"python <feature> example"` or `<module> site:docs.python.org` in your browser.
- **`pydoc` CLI**: `python -m pydoc json` opens module documentation.
- **Interactive REPL**: try snippets in `python` shell or `ipython` for quick experiments.

## Package & Plugin Discovery

- **PyPI (https://pypi.org)**: central index for Python packages. Search for automation libraries (e.g., "napalm nxos").
- **`pip search` alternative**: use `pip index versions <package>` or PyPI web UI; `pip search` is deprecated.
- **Project documentation**: always read the README or docs site linked on PyPI for usage examples.
- **Source code**: GitHub repositories often include sample playbooks and tests.

## Network Automation Libraries Cheat Sheet

| Library | Purpose | Key Commands | Learn More |
| --- | --- | --- | --- |
| **Nornir** | Inventory-driven, multi-threaded automation framework. | `pip install nornir`<br>`nornir.init_nornir()` | https://nornir.tech |
| **NAPALM** | Unified API for network device configuration/state retrieval. | `pip install napalm`
`from napalm import get_network_driver` | https://napalm.readthedocs.io |
| **pyATS / Genie** | Cisco testing & validation framework (state comparison, testbeds). | `pip install pyats[full]`
`from genie.testbed import load` | https://developer.cisco.com/pyats |
| **Netmiko** | Simplifies SSH connections & command execution. | `pip install netmiko`
`from netmiko import ConnectHandler` | https://github.com/ktbyers/netmiko |
| **Scrapli** | Fast, async-friendly network device driver library. | `pip install scrapli`
`from scrapli import Scrapli` | https://scrapli.github.io |
| **TextFSM** | Template-based parsing for CLI output. | `pip install textfsm` | https://github.com/google/textfsm |
| **Jinja2** | Templating engine for config generation. | `pip install jinja2` | https://jinja.palletsprojects.com |

### When to Choose What
- **Nornir**: coordinating many devices concurrently with a structured inventory.
- **NAPALM**: retrieving facts or pushing configuration via an abstracted API (e.g., standard interface to multiple vendors).
- **pyATS**: test automation, snapshots, and state diffing—perfect for pre/post-change validation.
- **Netmiko/Scrapli**: direct CLI automation when APIs are unavailable or as building blocks for custom tasks.
- **TextFSM**: parse CLI output into structured data for reporting or comparisons.
- **Jinja2**: render configuration templates, often combined with Nornir.

## Structuring Clean, Scalable Code

1. **Modularize**: split logic into functions/modules. Keep each function focused on a single concern.
2. **Abstract nested loops**: turn inner loops into helper functions so top-level workflows remain readable.
3. **Use configuration files**: store inventory, credentials, and templates outside of code (`yaml`, `json`).
4. **Tests**: start with unit tests for helpers and integration tests for workflows (`pytest`, pyATS jobs).
5. **Logging**: use Python’s `logging` module to track actions across devices.
6. **Concurrency**: prefer frameworks (Nornir, asyncio, concurrent.futures) instead of manual threading.
7. **Documentation**: docstrings + README sections for new modules, keep this `TUTORIAL.md` updated with discoveries.

## Continual Learning Workflow

1. **Identify the task** (e.g., automate VLAN deployment).
2. **Search** Python docs + relevant library docs for existing solutions.
3. **Prototype** in a sandbox or lab with a small inventory.
4. **Refine** by refactoring into functions/classes.
5. **Add tests** to lock behavior.
6. **Document** findings here to build your personalized reference.

> 💡 **Tip**: Whenever you learn a new module or pattern, capture a one-sentence summary and a minimal code snippet in this file. Over time, it becomes your network automation cookbook.
