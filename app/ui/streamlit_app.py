"""Streamlit UI for local workflow."""
from __future__ import annotations

import json

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.title("Cisco NX-OS VXLAN EVPN Fabric Designer")

tab_docs, tab_ask, tab_req, tab_build, tab_generate = st.tabs([
    "Upload Cisco docs",
    "Ask design questions",
    "Requirements",
    "Structured design",
    "Generate outputs",
])

with tab_docs:
    file = st.file_uploader("Upload PDF/TXT/MD")
    if file and st.button("Ingest"):
        r = requests.post(f"{API_BASE}/docs/ingest", files={"file": (file.name, file.getvalue())}, timeout=60)
        st.json(r.json())

with tab_ask:
    q = st.text_input("Doc-grounded question")
    if st.button("Ask") and q:
        st.json(requests.get(f"{API_BASE}/docs/ask", params={"question": q}, timeout=60).json())

with tab_req:
    req = st.text_area("Natural language requirements", height=180)
    if st.button("Parse requirements"):
        parsed = requests.post(f"{API_BASE}/design/parse", json={"requirements": req}, timeout=60).json()
        st.session_state["parsed"] = parsed
        st.json(parsed)

with tab_build:
    req_val = st.session_state.get("parsed")
    st.write("Design is built from requirements via policy+allocator.")
    if st.button("Build design"):
        req_text = req if req else "2 spines and 4 leafs"
        built = requests.post(f"{API_BASE}/design/build", json={"requirements": req_text}, timeout=60).json()
        st.session_state["design"] = built["design"]
        st.json(built)

with tab_generate:
    if st.button("Generate package") and st.session_state.get("design"):
        out = requests.post(f"{API_BASE}/generate/all", json={"design": st.session_state["design"]}, timeout=120).json()
        st.json(out)
