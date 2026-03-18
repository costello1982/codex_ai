# Cisco NX-OS VXLAN EVPN Fabric Automation (Nornir + scrapli + pyATS + OpenWebUI)

This repository provides an automated workflow for a Cisco NX-OS EVPN fabric with:

- Spine / Leaf / Border-Leaf roles
- vPC on leaf pairs
- Border Gateway (DCI) interconnect on border-leaf nodes
- Unnumbered underlay links
- OSPF underlay
- BGP EVPN overlay
- Dynamic subnet-based BGP neighbor onboarding (`bgp listen range`) to keep leaf configs minimal

## Project structure

```text
.
├── automation/
│   └── nornir_deploy.py            # Deploy configs to devices with Nornir + scrapli
├── data/
│   └── fabric.json                 # Source-of-truth topology and policy data
├── generated/                      # Rendered NX-OS configs (created by script)
├── inventory/
│   ├── defaults.yaml               # Credentials + transport settings
│   ├── groups.yaml                 # Group metadata (spine/leaf/border_leaf)
│   └── hosts.yaml                  # Device inventory
├── openwebui/
│   └── nxos_fabric_assistant.py    # LLM integration against OpenWebUI-compatible endpoint
├── pyats/
│   ├── jobs/
│   │   └── vxlan_job.py            # pyATS job file
│   ├── tests/
│   │   └── test_vxlan_evpn.py      # Validation suite
│   └── testbed_example.yaml        # Example testbed definition
├── scripts/
│   └── generate_configs.py         # JSON + Jinja generator
├── templates/
│   └── nxos_vxlan_evpn.j2          # NX-OS config template
└── requirements.txt
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 1) Generate configs (Jinja + JSON)

```bash
python3 scripts/generate_configs.py
```

The generated files are written into `generated/<hostname>.cfg`.

## 2) Deploy via Nornir + scrapli

Update credentials in `inventory/defaults.yaml`, then run:

```bash
python3 automation/nornir_deploy.py
```

Post-deploy, each host is checked with:

- `show bgp l2vpn evpn summary`

## 3) Validate with pyATS

Update `pyats/testbed_example.yaml` with real device details, then run:

```bash
easypy pyats/jobs/vxlan_job.py --testbed-file pyats/testbed_example.yaml
```

Current validations include:

- OSPF adjacency checks
- EVPN BGP summary checks
- NVE peer checks (non-spine devices)

## 4) LLM integration (OpenWebUI)

Set environment variables and run the helper:

```bash
export OPENWEBUI_BASE_URL="http://<openwebui-host>:3000"
export OPENWEBUI_API_KEY="<token-if-needed>"
python3 openwebui/nxos_fabric_assistant.py
```

This sends the `data/fabric.json` payload to your OpenWebUI OpenAI-compatible endpoint and returns deployment guidance/checklists.

## Notes on dynamic BGP neighbors

To minimize repetitive leaf configuration, template logic uses `bgp listen range` with a subnet (not specific IP neighbors) for EVPN peer onboarding.

- Spines listen for leaf loopbacks in a fabric subnet.
- Leafs listen for spine loopbacks using the loopback pool subnet.

Adjust listen ranges in `data/fabric.json`:

- `fabric.bgp_listen_subnet`
- `fabric.loopback_pool`
