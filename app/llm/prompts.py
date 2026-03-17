"""Prompt templates used by the LLM orchestration layer."""

REQUIREMENT_EXTRACTION_PROMPT = """
You are a network design intent parser.
Return strict JSON with keys:
fabric_name, site_name, site_id, spine_count, total_leaf_count, border_leaf_count,
vpc_pair_count, interconnect_requested, underlay_protocol, overlay_asn,
tenant_count, missing_parameters, warnings.
Do not invent values that are not provided. Put unknowns in missing_parameters.
Input: {requirements}
"""

DOC_QA_PROMPT = """
Answer the network design question using only provided context snippets.
Include an array named citations with source + page metadata.
Question: {question}
Context: {context}
"""
