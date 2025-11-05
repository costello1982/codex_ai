# Jinja-Driven VXLAN EVPN Bootstrap Examples

This directory mirrors the structure of the `examples/` folder but focuses on
**template-based automation**. Each script is saturated with comments so that a
beginner can understand the purpose of every section before adapting it to a
production fabric.

## Why Jinja?

* **Consistency** – The template enforces identical configuration blocks across
your fabric which prevents drift.
* **Speed** – Adding a new switch type often becomes a matter of extending the
JSON data instead of writing new Python logic.
* **Modularity** – Business intent (the JSON file) lives separately from the
rendering logic which makes code reviews and change control easier.

There are still times where generating commands programmatically in Python is
useful (for example, when you need to react to telemetry or device state in
real time). Jinja excels when you know the desired configuration up-front and
want to stamp it out in a deterministic way.

## Repository Contents

| File | Description |
| ---- | ----------- |
| `fabric_variables.json` | Declarative source of truth for fabric attributes such as device roles, loopback IDs, vPC domains, multicast group, and BGP ASN. |
| `templates/device_full_config.j2` | Production-ready configuration template. Feature enablement, underlay, and overlay blocks are rendered conditionally based on device role. |
| `render_fabric_configs.py` | Offline helper that renders per-switch configuration files into `rendered-configs/`. Useful for design reviews or uploading into Git for change control. |
| `deploy_fabric_configs.py` | Netmiko-powered workflow that renders the template and pushes it to Nexus switches with a mandatory diff/confirm step. |

Feel free to duplicate the template or add new ones (for example, a dedicated
underlay template) and swap them in by name when rendering. Jinja is flexible
and you can even call multiple templates in a single Python script to compose a
final configuration.

## JSON vs. YAML vs. Spreadsheet

JSON is used here because it is easy to read, version, and parse with the
standard library. If your team already tracks fabric details in a spreadsheet,
export it to JSON/CSV and convert on the fly. YAML is equally valid—simply swap
`json.load` for `yaml.safe_load` (after installing PyYAML) if you prefer the
syntax. The key point is to keep the source of truth outside of your Python so
changes can be reviewed without digging through code diffs.

## Operational Workflow

1. Update `fabric_variables.json` with the new switch or feature details.
2. Run `python render_fabric_configs.py` to create candidate configs.
3. Review the generated files (`rendered-configs/<hostname>.cfg`).
4. When ready, execute `python deploy_fabric_configs.py`, supply your
   credentials, inspect the diff, and explicitly approve the commit.
5. Archive the rendered configs in Git to create a rollback point. If you need
   to undo a change, simply re-render the last known-good JSON and push it.

## Extending the Template

* To add **new features** (for example, telemetry streaming or additional VRFs),
  extend the JSON with the required metadata and update `device_full_config.j2`.
* For **role-specific changes** (like unique feature sets on border gateways),
  add new conditionals in the template or break the template into smaller files
  and include them dynamically.
* If you grow beyond JSON, consider plugging these scripts into **Nornir** so
you can parallelize deployments and tie into inventory plugins you already use.

## Dependencies

* Python 3.9+
* `jinja2`
* `netmiko`

Install them with:

```bash
pip install jinja2 netmiko
```

Running inside a virtual environment is strongly recommended to keep packages
isolated from the system Python.
