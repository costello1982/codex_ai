"""Topology graph helpers."""
from __future__ import annotations

import networkx as nx


def graph_to_dot(graph: nx.Graph) -> str:
    lines = ["graph fabric {"]
    for node in graph.nodes:
        lines.append(f'  "{node}";')
    for a, b in graph.edges:
        lines.append(f'  "{a}" -- "{b}";')
    lines.append("}")
    return "\n".join(lines)
