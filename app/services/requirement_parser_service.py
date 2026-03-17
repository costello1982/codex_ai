"""Natural language requirement parser into strict intent."""
from __future__ import annotations

import re

from app.models.design_models import RequirementIntent


class RequirementParserService:
    """Hybrid parser: deterministic regex extraction + explicit missing fields."""

    def parse(self, text: str) -> RequirementIntent:
        lower = text.lower()

        def get_count(pattern: str, default: int = 0) -> int:
            m = re.search(pattern, lower)
            return int(m.group(1)) if m else default

        spines = get_count(r"(\d+)\s+spines?")
        total_leafs = get_count(r"(\d+)\s+leaf")
        border = get_count(r"(\d+)\s+(?:of\s+the\s+)?leafs?\s+(?:acting\s+as\s+)?border")
        vpc_pair = 1 if "vpc" in lower and "pair" in lower else 0
        interconnect = "interconnect" in lower or "another vxlan" in lower
        intent = RequirementIntent(
            spine_count=spines or 2,
            total_leaf_count=total_leafs or 4,
            border_leaf_count=border or (2 if "border" in lower else 0),
            vpc_pair_count=vpc_pair,
            interconnect_requested=interconnect,
        )
        if "site" not in lower:
            intent.missing_parameters.append("site_id")
        if "asn" not in lower:
            intent.missing_parameters.append("overlay_asn")
        return intent
