# NX-OS VXLAN EVPN Fabric Designer (Enterprise-Style, Local)

A local Python platform that converts natural-language data-center requirements into **structured intent**, validates policy constraints, then renders deterministic Cisco NX-OS templates and topology artifacts.

## Why this is safer than direct LLM-to-config generation

- LLM is only used for intent understanding and doc-grounded guidance.
- Final configs are generated from **validated Pydantic models + deterministic allocation + Jinja2 templates**.
- Missing values are surfaced via assumptions/warnings, policy defaults, or deterministic allocators.
- Topology and configs come from the same design object, preventing drift.

## Architecture

1. **Doc ingestion/RAG** (`app/services/doc_ingest_service.py`, `app/llm/retriever.py`)
2. **Requirement parsing** (`app/services/requirement_parser_service.py`)
3. **Design builder + policy engine** (`design_builder_service.py`, `policy_engine_service.py`)
4. **Deterministic allocator** (`allocator_service.py`)
5. **Validation** (`validation_service.py`)
6. **Config rendering** (`config_renderer_service.py`, `app/templates/nxos/*.j2`)
7. **Topology generation** (`topology_service.py`)
8. **Reporting/package** (`report_service.py`)
9. **FastAPI + Streamlit** (`app/api`, `app/ui/streamlit_app.py`)

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run API

```bash
uvicorn app.api.main:app --reload
```

## Run Streamlit

```bash
streamlit run app/ui/streamlit_app.py
```

## Ingest Cisco docs

```bash
curl -X POST -F "file=@app/data/docs/sample_guide.txt" http://localhost:8000/docs/ingest
```

## Parse/build/generate with API

```bash
curl -X POST http://localhost:8000/design/parse -H "content-type: application/json" \
  -d '{"requirements":"I want a data center with 2 spines, 8 leaf switches, a pair of border leaf switches, and one pair of leafs in vPC that interconnects to another VXLAN EVPN site"}'

curl -X POST http://localhost:8000/design/build -H "content-type: application/json" \
  -d '{"requirements":"I want a data center with 2 spines, 8 leaf switches, a pair of border leaf switches, and one pair of leafs in vPC that interconnects to another VXLAN EVPN site"}'
```

Then pass returned `design` object to:

```bash
curl -X POST http://localhost:8000/generate/all -H "content-type: application/json" -d @payload.json
```

## Example scenario included

`app/data/examples/sample_requirements.txt` implements:
- 2 spines
- 8 total leafs
- 2 border leafs
- 1 vPC pair
- EVPN DCI interconnect to remote site

The builder interprets total leaf count as inclusive of border + vPC members; regular leafs are calculated and documented via assumptions.

## Test

```bash
pytest -q
```

## Limitations

- Requirement parser is deterministic regex-based baseline.
- RAG endpoint returns retrieved chunks; no external hosted LLM dependency by default.
- Templates are production-style scaffolds, not full feature-complete Cisco libraries.

## Roadmap

- pyATS/Genie post-render validation pipeline
- Nornir/Netmiko deployment workers
- GitOps review gates and PR approval workflow
- Expanded Cisco role templates and EVPN multi-site depth
- Source-of-truth/IPAM integration
